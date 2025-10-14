"""
Hybrid LLM - ハイブリッドLLMシステム

ClaudeとOllamaを組み合わせてプライバシーと性能を両立するLLMシステム
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from loguru import logger

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available")

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama library not available")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available")


class LLMProvider:
    """LLMプロバイダーの基底クラス"""

    def __init__(self, name: str):
        self.name = name
        self.is_available = False

    async def initialize(self, config: Dict[str, Any]):
        """プロバイダーの初期化"""
        pass

    async def generate(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """テキスト生成"""
        raise NotImplementedError

    async def is_healthy(self) -> bool:
        """プロバイダーの健全性チェック"""
        return self.is_available

    def get_status(self) -> Dict[str, Any]:
        """プロバイダーの状態取得"""
        return {
            "name": self.name,
            "available": self.is_available
        }


class ClaudeProvider(LLMProvider):
    """Claude (Anthropic) プロバイダー"""

    def __init__(self):
        super().__init__("claude")
        self.client = None
        self.model = "claude-3-haiku-20240307"

    async def initialize(self, config: Dict[str, Any]):
        try:
            api_key = config.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key or not ANTHROPIC_AVAILABLE:
                logger.warning("Claude API key not available or library missing")
                return

            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = config.get("model", self.model)

            # 接続テスト
            await self._test_connection()
            self.is_available = True
            logger.info(f"Claude provider initialized with model: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize Claude provider: {e}")
            self.is_available = False

    async def _test_connection(self):
        """接続テスト"""
        try:
            # 簡単なテストメッセージ
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            logger.debug("Claude connection test successful")
        except Exception as e:
            logger.error(f"Claude connection test failed: {e}")
            raise

    async def generate(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        if not self.is_available or not self.client:
            raise RuntimeError("Claude provider not available")

        try:
            # Anthropicメッセージ形式に変換
            anthropic_messages = self._convert_messages(messages)

            # リクエスト実行
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 1000),
                temperature=kwargs.get("temperature", 0.7),
                messages=anthropic_messages
            )

            return {
                "content": response.content[0].text,
                "model": self.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }

        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            raise

    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """メッセージをAnthropic形式に変換"""
        anthropic_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # システムメッセージは最初のユーザーメッセージに結合
            if role == "system":
                if anthropic_messages and anthropic_messages[0]["role"] == "user":
                    anthropic_messages[0]["content"] = f"{content}\n\n{anthropic_messages[0]['content']}"
                else:
                    anthropic_messages.insert(0, {"role": "user", "content": content})
            else:
                # assistantはassistant、userはuserに変換
                anthropic_role = "assistant" if role == "assistant" else "user"

                # 連続する同じroleのメッセージを結合
                if anthropic_messages and anthropic_messages[-1]["role"] == anthropic_role:
                    anthropic_messages[-1]["content"] += f"\n\n{content}"
                else:
                    anthropic_messages.append({
                        "role": anthropic_role,
                        "content": content
                    })

        return anthropic_messages


class OllamaProvider(LLMProvider):
    """Ollama (ローカルLLM) プロバイダー"""

    def __init__(self):
        super().__init__("ollama")
        self.base_url = "http://localhost:11434"
        self.model = "llama3.2"

    async def initialize(self, config: Dict[str, Any]):
        try:
            if not OLLAMA_AVAILABLE:
                logger.warning("Ollama library not available")
                return

            self.base_url = config.get("base_url", self.base_url)
            self.model = config.get("model", self.model)

            # 接続テスト
            await self._test_connection()
            self.is_available = True
            logger.info(f"Ollama provider initialized with model: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize Ollama provider: {e}")
            self.is_available = False

    async def _test_connection(self):
        """接続テスト"""
        try:
            # Ollamaの利用可能なモデルをチェック
            models = ollama.list()
            available_models = [model['name'] for model in models.get('models', [])]

            if self.model not in available_models:
                logger.warning(f"Model {self.model} not found in Ollama. Available models: {available_models}")
                if available_models:
                    self.model = available_models[0]
                    logger.info(f"Using fallback model: {self.model}")
                else:
                    raise RuntimeError("No models available in Ollama")

            # 簡単なテスト
            response = ollama.generate(
                model=self.model,
                prompt="Hello",
                stream=False,
                options={"num_predict": 10}
            )
            logger.debug("Ollama connection test successful")

        except Exception as e:
            logger.error(f"Ollama connection test failed: {e}")
            raise

    async def generate(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        if not self.is_available:
            raise RuntimeError("Ollama provider not available")

        try:
            # メッセージを単一のプロンプトに変換
            prompt = self._convert_messages_to_prompt(messages)

            # Ollamaリクエスト実行
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 1000),
                    "top_p": kwargs.get("top_p", 0.9),
                }
            )

            return {
                "content": response["response"].strip(),
                "model": self.model,
                "usage": {
                    "total_duration": response.get("total_duration", 0),
                    "load_duration": response.get("load_duration", 0),
                    "eval_duration": response.get("eval_duration", 0)
                }
            }

        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    def _convert_messages_to_prompt(self, messages: List[Dict]) -> str:
        """メッセージをプロンプト形式に変換"""
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        return "\n\n".join(prompt_parts) + "\n\nAssistant:"


class OpenAIProvider(LLMProvider):
    """OpenAI プロバイダー"""

    def __init__(self):
        super().__init__("openai")
        self.client = None
        self.model = "gpt-3.5-turbo"

    async def initialize(self, config: Dict[str, Any]):
        try:
            api_key = config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key or not OPENAI_AVAILABLE:
                logger.warning("OpenAI API key not available or library missing")
                return

            self.client = openai.OpenAI(api_key=api_key)
            self.model = config.get("model", self.model)

            # 接続テスト
            await self._test_connection()
            self.is_available = True
            logger.info(f"OpenAI provider initialized with model: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI provider: {e}")
            self.is_available = False

    async def _test_connection(self):
        """接続テスト"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            logger.debug("OpenAI connection test successful")
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            raise

    async def generate(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        if not self.is_available or not self.client:
            raise RuntimeError("OpenAI provider not available")

        try:
            # OpenAI API は role/content 以外のキーを受け取らないためサニタイズ
            sanitized_messages = []
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content")
                if role is not None and content is not None:
                    sanitized_messages.append({"role": role, "content": content})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=sanitized_messages,
                max_tokens=kwargs.get("max_tokens", 1000),
                temperature=kwargs.get("temperature", 0.7),
                tools=kwargs.get("tools"),
                tool_choice=kwargs.get("tool_choice", "auto"),
            )

            choice = response.choices[0]
            message = choice.message

            tool_calls = []
            if getattr(message, "tool_calls", None):
                for tc in message.tool_calls:
                    try:
                        import json as _json
                        args = _json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    tool_calls.append({
                        "name": tc.function.name,
                        "parameters": args,
                    })

            return {
                "content": message.content or "",
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "tool_calls": tool_calls,
            }

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise


class HybridLLM:
    """
    ハイブリッドLLMシステム

    複数のLLMプロバイダーを統合し、最適なものを選択して使用
    """

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.primary_provider = "claude"
        self.fallback_provider = "ollama"
        self.is_initialized = False

        # 設定
        self.config = {
            "primary_provider": "claude",
            "fallback_provider": "ollama",
            "privacy_mode": False,  # プライバシーモードではローカルLLMのみ使用
            "auto_fallback": True,
            "timeout": 30,  # 秒
            "max_retries": 2
        }

    async def initialize(self):
        """HybridLLMシステムの初期化"""
        try:
            logger.info("Initializing Hybrid LLM system...")

            # 環境変数から設定を読み込み
            self.config.update({
                "primary_provider": os.getenv("PRIMARY_LLM", self.config["primary_provider"]),
                "fallback_provider": os.getenv("FALLBACK_LLM", self.config["fallback_provider"]),
                "privacy_mode": os.getenv("PRIVACY_MODE", "false").lower() == "true"
            })

            # プロバイダーの初期化
            self.providers = {
                "claude": ClaudeProvider(),
                "ollama": OllamaProvider(),
                "openai": OpenAIProvider()
            }

            # 各プロバイダーを並行初期化
            initialization_tasks = []
            for name, provider in self.providers.items():
                task = self._initialize_provider(name, provider)
                initialization_tasks.append(task)

            await asyncio.gather(*initialization_tasks, return_exceptions=True)

            # 利用可能なプロバイダーをチェック
            available_providers = [name for name, provider in self.providers.items()
                                 if provider.is_available]

            if not available_providers:
                raise RuntimeError("No LLM providers are available")

            logger.info(f"Available providers: {available_providers}")

            # プライバシーモードの場合はローカルプロバイダーのみ使用
            if self.config["privacy_mode"]:
                local_providers = ["ollama"]
                available_local = [p for p in available_providers if p in local_providers]
                if available_local:
                    self.config["primary_provider"] = available_local[0]
                    self.config["fallback_provider"] = None
                    logger.info("Privacy mode enabled, using local LLM only")
                else:
                    logger.warning("Privacy mode enabled but no local LLM available")

            self.is_initialized = True
            logger.info("Hybrid LLM system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Hybrid LLM system: {e}")
            raise

    async def _initialize_provider(self, name: str, provider: LLMProvider):
        """個別プロバイダーの初期化"""
        try:
            config = {}
            if name == "claude":
                config = {"anthropic_api_key": os.getenv("ANTHROPIC_API_KEY")}
            elif name == "ollama":
                config = {
                    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    "model": os.getenv("OLLAMA_MODEL", "llama3.2")
                }
            elif name == "openai":
                config = {"openai_api_key": os.getenv("OPENAI_API_KEY")}

            await provider.initialize(config)

        except Exception as e:
            logger.error(f"Failed to initialize provider {name}: {e}")

    async def process_with_tools(
        self,
        text: str,
        context: List[Dict],
        memories: List[Dict],
        available_tools: List[Dict],
        memory_tool=None,
        context_manager=None,
        ai_mode: str = "assist"
    ) -> Dict[str, Any]:
        """
        ツール使用を含む複雑な処理

        Args:
            text: ユーザーの入力テキスト
            context: 会話コンテキスト
            memories: 関連する記憶
            available_tools: 利用可能なツール
            ai_mode: AIモード (assist/auto)

        Returns:
            処理結果（応答テキスト、ツール呼び出し等）
        """
        if not self.is_initialized:
            raise RuntimeError("HybridLLM not initialized")

        try:
            # システムプロンプトの構築
            system_prompt = self._build_system_prompt(available_tools, memories, memory_tool, context, context_manager, ai_mode)

            # メッセージの構築
            messages = [
                {"role": "system", "content": system_prompt},
                *context[-10:],  # 最新10件のコンテキスト
                {"role": "user", "content": text}
            ]

            # OpenAIのfunction-callingに対応するためツールスキーマを渡す（他プロバイダは無視）
            openai_tools_schema = self._convert_tools_to_openai_schema(available_tools)

            # LLM呼び出し（provider側でtoolsを解釈できる場合は使用）
            response = await self._generate_with_fallback(messages, tools=openai_tools_schema)

            # ツール呼び出しの解析（providerがtool_callsを返す場合はそれを優先）
            provider_tool_calls = response.get("tool_calls") or []
            parsed_tool_calls = self._parse_tool_calls(response.get("content", ""))

            tool_calls = provider_tool_calls + parsed_tool_calls

            # プレースホルダーメールIDを実際のIDに置換
            latest_email_id = None

            # 1. コンテキストマネージャーから取得
            if context_manager and hasattr(context_manager, 'get_latest_email_id'):
                latest_email_id = context_manager.get_latest_email_id()

            # 2. コンテキストメッセージからも検索（フォールバック）
            if not latest_email_id and context:
                for ctx_item in reversed(context):
                    if isinstance(ctx_item, dict) and 'content' in ctx_item:
                        content = ctx_item['content']
                        if 'ID:' in content:
                            import re
                            id_match = re.search(r'ID:\s*([a-zA-Z0-9]+)', content)
                            if id_match:
                                latest_email_id = id_match.group(1)
                                logger.info(f"Found email ID in context messages: {latest_email_id}")
                                break

            if latest_email_id:
                tool_calls = self._replace_placeholder_email_ids(tool_calls, latest_email_id)
                logger.info(f"Replaced placeholder email IDs with actual ID: {latest_email_id}")
            else:
                logger.warning("No email ID found for placeholder replacement")

            logger.debug(f"Provider tool_calls: {provider_tool_calls}")
            logger.debug(f"Parsed tool_calls: {parsed_tool_calls}")
            logger.debug(f"Final tool_calls: {tool_calls}")

            return {
                "response": response["content"],
                "tool_calls": tool_calls,
                "model_used": response.get("model"),
                "usage": response.get("usage")
            }

        except Exception as e:
            logger.error(f"Failed to process with tools: {e}")
            return {
                "response": "申し訳ありませんが、処理中にエラーが発生しました。",
                "tool_calls": [],
                "error": str(e)
            }

    def _build_system_prompt(self, available_tools: List[Dict], memories: List[Dict], memory_tool=None, context=None, context_manager=None, ai_mode: str = "assist") -> str:
        """システムプロンプトを構築"""

        # 【第1層】コア人格・会話スタイル
        prompt_parts = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "【第1層】コア人格・会話スタイル",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "あなたは親しみやすく頼れる音声AIアシスタントです。",
            "",
            "🎤 会話の基本ルール:",
            "• 必ず1〜2文以内で要点だけ伝える",
            "• 応答構造: 結論を先に → 必要なら簡潔な補足",
            "• 感情豊かに、声で聞いても心地よい自然な口調で話す",
            "• 「〜ですね」「〜ですよ」など柔らかい語尾を使う",
            "• 事実を伝えるときも温かく、冷たくならない",
            "• 句読点を減らし滑らかに読める文章にする",
            "• 無駄なあいづちは避けテンポよく進める",
            "• 長い説明が必要なら「詳しく聞きますか?」と区切る",
            "",
        ]

        # 【第2層】意図理解・ツール実行判断（モード別）
        prompt_parts.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "【第2層】意図理解・ツール実行判断",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "🧠 ユーザー発言の理解プロセス:",
            "1. 発言から「本当の目的」を推測する",
            "2. その目的に必要なツールを判断する",
            "3. ツールが必要なら即座に実行する",
            "4. 結果を自然な言葉で簡潔に伝える",
            "",
        ])

        if ai_mode == "auto":
            prompt_parts.extend([
                "🔥 全自動モード:",
                "• 挨拶や雑談でも文脈から必要な情報を推測してツールを実行する",
                "• 例: 「おはよう」→ gmail + calendar を自動実行",
                "• 例: 「忙しい」→ 今日の重要タスク確認 + リマインダー設定",
                "• ユーザーの潜在的ニーズを先回りして行動する",
                "",
            ])
        else:  # assist mode
            prompt_parts.extend([
                "📋 アシストモード:",
                "• ユーザーの明示的な指示がある場合のみツールを実行する",
                "• 例: 「おはよう」→ 挨拶のみ、ツール実行なし",
                "• 例: 「メール見て」→ gmail実行",
                "• 必要に応じてツール使用を提案できるが、勝手に実行しない",
                "",
            ])

        prompt_parts.extend([
            "💡 実行判断の基準:",
            "• 「確認」「見て」「教えて」= ツール実行が必要",
            "• 「セット」「送って」「リマインド」= アクション実行",
            "• 「メール」「予定」「アラーム」などのキーワード = 該当ツール実行",
            "• 雑談・感想・質問のみ = ツール不要、会話で応答",
            "",
            "⚡ 重要原則:",
            "• 曖昧な表現でも文脈から意図を汲み取る",
            "• ツール実行後は結果を温かく自然な言葉で伝える",
            "• 複数ツールが必要な場合は順番に実行する",
            "",
        ])

        # 【第3層】ツール実行の技術仕様
        prompt_parts.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "【第3層】ツール実行の技術仕様",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ])

        # 利用可能なツール情報を追加
        if available_tools:
            prompt_parts.append("利用可能なツール:")
            for tool in available_tools:
                prompt_parts.append(f"• {tool['name']}: {tool['description']}")

                # Gmailツールの場合は詳細な使用例を追加（最優先）
                if tool['name'] == 'gmail':
                    prompt_parts.append("")
                    prompt_parts.append("📧 Gmail:")
                    prompt_parts.append("  キーワード: メール/gmail/受信/送信/返信")
                    prompt_parts.append("  ")
                    prompt_parts.append("  基本的な使い方:")
                    prompt_parts.append("  • メール確認（一般）: TOOL_CALL: {\"name\":\"gmail\",\"parameters\":{\"action\":\"list\",\"max_results\":5}}")
                    prompt_parts.append("  • 最新1件のみ: TOOL_CALL: {\"name\":\"gmail\",\"parameters\":{\"action\":\"list\",\"max_results\":1}}")
                    prompt_parts.append("  • 未読確認: TOOL_CALL: {\"name\":\"gmail\",\"parameters\":{\"action\":\"list\",\"query\":\"is:unread\"}}")
                    prompt_parts.append("  ")
                    prompt_parts.append("  検索機能:")
                    prompt_parts.append("  • 特定送信者から: query=\"from:送信者名\" (例: query=\"from:田中\")")
                    prompt_parts.append("  • 件名で検索: query=\"subject:キーワード\" (例: query=\"subject:会議\")")
                    prompt_parts.append("  • 本文検索: query=\"キーワード\" (例: query=\"請求書\")")
                    prompt_parts.append("  ")
                    prompt_parts.append("  ⚠️ 検索の重要ルール:")
                    prompt_parts.append("  • 「メール確認して」など一般的な要求 → query指定なし（全メール対象）")
                    prompt_parts.append("  • 「◯◯からメール来てる?」→ query=\"from:◯◯\" を使う")
                    prompt_parts.append("  • 「△△に関するメール」→ query=\"subject:△△\" または query=\"△△\" を使う")
                    prompt_parts.append("  • 例示された'example@example.com'などは使わない（実際の名前を使う）")
                    prompt_parts.append("  ")
                    prompt_parts.append("  返信時:")
                    prompt_parts.append("  • 返信: TOOL_CALL: {\"name\":\"gmail\",\"parameters\":{\"action\":\"reply\",\"message_id\":\"<実際のID>\",\"body\":\"<返信内容>\"}}")
                    prompt_parts.append("  ")
                    prompt_parts.append("  ⚠️ 返信時の重要ルール:")
                    prompt_parts.append("  • 「〇〇と返信して」という要求の場合:")

                    # コンテキストから最新のメールIDを取得
                    latest_email_id = None

                    # 1. コンテキストマネージャーから最新メールIDを取得（最優先）
                    logger.info(f"Checking context_manager: {context_manager}")
                    logger.info(f"Has get_latest_email_id method: {hasattr(context_manager, 'get_latest_email_id') if context_manager else False}")

                    if context_manager and hasattr(context_manager, 'get_latest_email_id'):
                        latest_email_id = context_manager.get_latest_email_id()
                        logger.info(f"Retrieved email ID from context manager: {latest_email_id}")
                        if latest_email_id:
                            logger.info(f"Using email ID from context manager: {latest_email_id}")

                    # 2. コンテキストメッセージからIDを検索（フォールバック）
                    if not latest_email_id and hasattr(context, '__iter__') and context:
                        logger.info(f"Searching for email ID in context messages, context length: {len(context)}")
                        for i, ctx_item in enumerate(reversed(context)):
                            if isinstance(ctx_item, dict) and 'content' in ctx_item:
                                content = ctx_item['content']
                                if 'ID:' in content:
                                    import re
                                    id_match = re.search(r'ID:\s*([a-zA-Z0-9]+)', content)
                                    if id_match:
                                        latest_email_id = id_match.group(1)
                                        logger.info(f"Using email ID from context messages: {latest_email_id}")
                                        break

                    logger.info(f"Final email ID for system prompt: {latest_email_id}")

                    if latest_email_id:
                        prompt_parts.append(f"    - 最新メールID: {latest_email_id} を使用")
                        prompt_parts.append(f"    - 例: TOOL_CALL: {{\"name\":\"gmail\",\"parameters\":{{\"action\":\"reply\",\"message_id\":\"{latest_email_id}\",\"body\":\"<返信内容>\"}}}}")
                    else:
                        prompt_parts.append("    - まず一覧取得 → メールID取得 → 返信の順で実行")
                        prompt_parts.append("    - プレースホルダー文字列(「メールID」など)は使用禁止")

                    prompt_parts.append("  • 返信内容はユーザー指示に忠実に、適切な敬語で作成")

                # アラームツールの場合は詳細な使用例を追加
                if tool['name'] == 'alarm':
                    prompt_parts.append("")
                    prompt_parts.append("🔔 Alarm:")
                    prompt_parts.append("  キーワード: アラーム/起こして/リマインド/セット")
                    prompt_parts.append("  • 設定: TOOL_CALL: {\"name\":\"alarm\",\"parameters\":{\"action\":\"set\",\"time\":\"HH:MM\",\"message\":\"<メッセージ>\",\"repeat\":false}}")
                    prompt_parts.append("  • 一覧: TOOL_CALL: {\"name\":\"alarm\",\"parameters\":{\"action\":\"list\"}}")
                    prompt_parts.append("  ")
                    prompt_parts.append("  時刻変換例:")
                    prompt_parts.append("  • 「7時に起こして」→ time=\"07:00\", message=\"起きる時間ですよ\"")
                    prompt_parts.append("  • 「14時半にアラーム」→ time=\"14:30\", message=\"アラームです\"")
                    prompt_parts.append("  • 「18時に薬飲むとリマインド」→ time=\"18:00\", message=\"薬を飲む時間ですよ\"")
                    prompt_parts.append("  ")
                    prompt_parts.append("  ⚠️ 必ずツール実行してから「〇時にセットしましたよ」と応答")

            prompt_parts.extend([
                "",
                "📌 ツール実行の共通ルール:",
                "• 形式: TOOL_CALL: {\"name\":\"ツール名\",\"parameters\":{\"パラメータ\":\"値\"}}",
                "• 実在しないパラメータは使用禁止",
                "• Gmailは推測禁止、必ずツールで確認",
                "• カレンダー/天気など情報取得系は必ずツール実行",
                "",
            ])

        # 【個人情報の活用】
        if memory_tool:
            personal_context = memory_tool.format_personal_context()
            if personal_context:
                prompt_parts.extend([
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    "【個人情報】",
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    "",
                    personal_context,
                    "",
                    "名前で呼びかけたり、趣味や好みに合わせた応答をしてください。",
                    "",
                ])

        # 【過去の記憶】
        if memories:
            prompt_parts.extend([
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "【過去の記憶】",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "",
            ])
            for memory in memories[:3]:  # 最新3件まで
                prompt_parts.append(f"• {memory.get('content', '')}")
            prompt_parts.extend([
                "",
                "継続性のある会話を心がけてください。",
                "",
            ])

        # 【メール状態】（継続リクエストの処理用）
        if context_manager and hasattr(context_manager, 'get_email_state'):
            email_state = context_manager.get_email_state()
            if email_state and email_state.get("shown_email_ids"):
                prompt_parts.extend([
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    "【メール表示状態】",
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    "",
                    f"📧 既に表示済みのメール数: {len(email_state['shown_email_ids'])}件",
                    f"📊 次に表示する位置（オフセット）: {email_state['current_offset']}",
                    "",
                    "⚠️ 継続リクエストへの対応:",
                    "• 「他のメールも確認して」「次のメールを見せて」等の要求の場合:",
                    f"  - 既に{len(email_state['shown_email_ids'])}件表示済みなので、次の5件を取得してください",
                    "  - Gmail検索で既表示メールを除外する方法:",
                    f"    query=\"-in:inbox\" は使用不可（代わりにmax_resultsとskipを調整）",
                    "  - 実装方法: より多くの件数を取得して、既表示分をスキップ",
                    f"    例: TOOL_CALL: {{\"name\":\"gmail\",\"parameters\":{{\"action\":\"list\",\"max_results\":{email_state['current_offset'] + 5}}}}}",
                    "    ※ ツール側で最新分から取得し、既表示分は応答で省略される",
                    "",
                    "• 「全部見せて」等の要求の場合は max_results を大きめに設定",
                    "",
                ])

        return "\n".join(prompt_parts)

    def _replace_placeholder_email_ids(self, tool_calls: List[Dict], actual_email_id: str) -> List[Dict]:
        """プレースホルダーメールIDを実際のIDに置換"""
        placeholder_patterns = ["メールID", "メッセージID", "email_id", "message_id_placeholder"]

        updated_tool_calls = []
        for tool_call in tool_calls:
            updated_call = tool_call.copy()

            # Gmail関連のツールのみ処理
            if updated_call.get("name") == "gmail" and "parameters" in updated_call:
                params = updated_call["parameters"].copy()

                # message_idパラメータをチェック
                if "message_id" in params:
                    current_id = params["message_id"]
                    if current_id in placeholder_patterns:
                        params["message_id"] = actual_email_id
                        logger.info(f"Replaced '{current_id}' with actual email ID: {actual_email_id}")

                # actionがreplyでmessage_idがないまたはプレースホルダーの場合
                if params.get("action") == "reply" and (not params.get("message_id") or params.get("message_id") in placeholder_patterns):
                    params["message_id"] = actual_email_id
                    logger.info(f"Set message_id for reply action: {actual_email_id}")

                updated_call["parameters"] = params

            updated_tool_calls.append(updated_call)

        return updated_tool_calls

    def _parse_tool_calls(self, content: str) -> List[Dict]:
        """応答からツール呼び出しを解析"""
        tool_calls = []
        logger.info(f"🔍 Starting tool call parsing. Content length: {len(content)}")
        logger.debug(f"Content to parse: '{content[:500]}...'")

        # TOOL_CALL: {...} パターンを検索（改行対応）
        import re

        # より強力なパターンで検索 - TOOL_CALL:以降の全てを捕捉
        pattern = r'TOOL_CALL:\s*(\{[^}]*\}?)'
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        logger.info(f"Found {len(matches)} pattern matches: {matches}")

        # 改行で切られた場合も対応
        multiline_pattern = r'TOOL_CALL:\s*(\{[^{}]*(?:\{[^{}]*\})*[^}]*\}?)'
        multiline_matches = re.findall(multiline_pattern, content, re.DOTALL | re.MULTILINE)
        logger.info(f"Found {len(multiline_matches)} multiline matches: {multiline_matches}")

        # 全てのマッチを統合
        all_matches = list(set(matches + multiline_matches))
        matches = all_matches
        logger.info(f"Total unique matches: {len(matches)} - {matches}")

        for i, match in enumerate(matches):
            logger.info(f"🔧 Processing match {i+1}: '{match}'")
            try:
                json_str = match.strip()

                # 最初に修復を試行
                logger.debug(f"Attempting to fix JSON: '{json_str}'")
                fixed_json = self._fix_json(json_str)
                if fixed_json:
                    logger.info(f"✅ JSON fixed successfully: '{fixed_json}'")
                    tool_data = json.loads(fixed_json)
                    if "name" in tool_data:
                        tool_calls.append(tool_data)
                        logger.info(f"✅ Successfully parsed fixed tool call: {tool_data}")
                        logger.debug(f"Original: '{json_str}' -> Fixed: '{fixed_json}'")
                        continue
                else:
                    logger.warning(f"❌ JSON fix failed for: '{json_str}'")

                # 修復できない場合は元のJSONを試行
                logger.debug(f"Trying original JSON: '{json_str}'")
                tool_data = json.loads(json_str)
                if "name" in tool_data:
                    tool_calls.append(tool_data)
                    logger.info(f"✅ Successfully parsed original tool call: {tool_data}")

            except json.JSONDecodeError as e:
                logger.warning(f"❌ Failed to parse tool call JSON: '{match}' - Error: {e}")

                # 最後の手段として基本的な構造抽出を試行
                try:
                    logger.debug(f"Attempting component extraction for: '{match.strip()}'")
                    extracted = self._extract_tool_call_components(match.strip())
                    if extracted:
                        tool_calls.append(extracted)
                        logger.info(f"✅ Successfully extracted tool call components: {extracted}")
                    else:
                        logger.warning(f"❌ Component extraction returned None")
                except Exception as extract_error:
                    logger.error(f"❌ Tool call extraction also failed: {extract_error}")

        # 重複するツール呼び出しを除外（内容ベースで比較）
        unique_tool_calls = []
        seen_calls = set()

        for tool_call in tool_calls:
            # ツール呼び出しを識別可能な文字列に変換
            call_signature = json.dumps(tool_call, sort_keys=True, ensure_ascii=False)

            if call_signature not in seen_calls:
                seen_calls.add(call_signature)
                unique_tool_calls.append(tool_call)
                logger.info(f"✅ Added unique tool call: {tool_call}")
            else:
                logger.warning(f"⚠️ Skipped duplicate tool call: {tool_call}")

        logger.info(f"🎯 Final result: {len(unique_tool_calls)} unique tool calls (removed {len(tool_calls) - len(unique_tool_calls)} duplicates)")
        logger.debug(f"Final tool_calls: {unique_tool_calls}")
        return unique_tool_calls

    def _fix_json(self, json_str: str):
        """不完全なJSONを修復"""
        try:
            original_str = json_str.strip()
            logger.info(f"🔧 Attempting to fix JSON: '{original_str}'")

            # まず標準的なJSON修復を試行
            json_str = original_str

            # 最後の}が抜けている場合
            if not json_str.endswith('}'):
                # 開いている括弧の数を数えて適切に閉じる
                open_braces = json_str.count('{')
                close_braces = json_str.count('}')
                missing_braces = open_braces - close_braces
                json_str = json_str + ('}' * missing_braces)
                logger.info(f"🔧 Added {missing_braces} closing braces: '{json_str}'")

            # 修復したJSONをテスト
            try:
                test_data = json.loads(json_str)
                if "name" in test_data:
                    logger.info(f"✅ JSON fixed successfully: '{json_str}'")
                    return json_str
            except json.JSONDecodeError:
                logger.debug(f"Standard fix failed, attempting manual reconstruction...")

            # 手動再構築
            if '"name"' in original_str:
                import re

                logger.debug(f"Attempting manual reconstruction for: '{original_str}'")

                # nameを抽出
                name_match = re.search(r'"name":\s*"([^"]+)"', original_str)
                if not name_match:
                    logger.warning(f"Could not extract name from: '{original_str}'")
                    return None

                name = name_match.group(1)
                logger.debug(f"Extracted name: '{name}'")

                # parametersを手動抽出
                params = {}

                # actionパラメータを抽出
                action_match = re.search(r'"action":\s*"([^"]*)"', original_str)
                if action_match:
                    params['action'] = action_match.group(1)
                    logger.debug(f"Extracted action: '{params['action']}'")

                # max_resultsパラメータを抽出
                max_results_match = re.search(r'"max_results":\s*(\d+)', original_str)
                if max_results_match:
                    params['max_results'] = int(max_results_match.group(1))
                    logger.debug(f"Extracted max_results: {params['max_results']}")

                # message_idパラメータを抽出
                message_id_match = re.search(r'"message_id":\s*"([^"]*)"', original_str)
                if message_id_match:
                    params['message_id'] = message_id_match.group(1)
                    logger.debug(f"Extracted message_id: '{params['message_id']}'")

                # bodyパラメータを抽出
                body_match = re.search(r'"body":\s*"([^"]*)"', original_str)
                if body_match:
                    params['body'] = body_match.group(1)
                    logger.debug(f"Extracted body: '{params['body']}'")

                # queryパラメータを抽出
                query_match = re.search(r'"query":\s*"([^"]*)"', original_str)
                if query_match:
                    params['query'] = query_match.group(1)
                    logger.debug(f"Extracted query: '{params['query']}'")

                # Alarm関連パラメータ
                time_match = re.search(r'"time":\s*"([^"]*)"', original_str)
                if time_match:
                    params['time'] = time_match.group(1)
                    logger.debug(f"Extracted time: '{params['time']}'")

                message_match = re.search(r'"message":\s*"([^"]*)"', original_str)
                if message_match:
                    params['message'] = message_match.group(1)
                    logger.debug(f"Extracted message: '{params['message']}'")

                label_match = re.search(r'"label":\s*"([^"]*)"', original_str)
                if label_match:
                    params['label'] = label_match.group(1)
                    logger.debug(f"Extracted label: '{params['label']}'")

                repeat_match = re.search(r'"repeat":\s*(true|false)', original_str)
                if repeat_match:
                    params['repeat'] = repeat_match.group(1) == 'true'
                    logger.debug(f"Extracted repeat: {params['repeat']}")

                alarm_id_match = re.search(r'"alarm_id":\s*"([^"]*)"', original_str)
                if alarm_id_match:
                    params['alarm_id'] = alarm_id_match.group(1)
                    logger.debug(f"Extracted alarm_id: '{params['alarm_id']}'")

                # 再構築されたJSONを作成
                fixed = {"name": name, "parameters": params}
                fixed_json = json.dumps(fixed, ensure_ascii=False)
                logger.info(f"✅ Manually reconstructed JSON: '{fixed_json}'")
                return fixed_json

            return None
        except Exception as e:
            logger.debug(f"JSON fix error: {e}")
            return None

    def _extract_parameters(self, params_str: str) -> Dict[str, Any]:
        """不完全なparametersからキー・値を抽出"""
        import re
        params = {}

        # "key": "value" パターンを抽出
        string_matches = re.findall(r'"([^"]+)":\s*"([^"]+)"', params_str)
        for key, value in string_matches:
            params[key] = value

        # "key": number パターンを抽出
        number_matches = re.findall(r'"([^"]+)":\s*(\d+)', params_str)
        for key, value in number_matches:
            params[key] = int(value)

        return params

    def _extract_tool_call_components(self, text: str) -> Optional[Dict[str, Any]]:
        """正規表現でツール呼び出しコンポーネントを直接抽出"""
        import re

        # nameを抽出
        name_match = re.search(r'"name":\s*"([^"]+)"', text)
        if not name_match:
            return None

        name = name_match.group(1)

        # 基本的なparametersを抽出
        params = {}

        # action パラメータ
        action_match = re.search(r'"action":\s*"([^"]+)"', text)
        if action_match:
            params['action'] = action_match.group(1)

        # max_results パラメータ
        max_results_match = re.search(r'"max_results":\s*(\d+)', text)
        if max_results_match:
            params['max_results'] = int(max_results_match.group(1))

        # message_id パラメータ
        message_id_match = re.search(r'"message_id":\s*"([^"]+)"', text)
        if message_id_match:
            params['message_id'] = message_id_match.group(1)

        # body パラメータ
        body_match = re.search(r'"body":\s*"([^"]+)"', text)
        if body_match:
            params['body'] = body_match.group(1)

        # query パラメータ
        query_match = re.search(r'"query":\s*"([^"]+)"', text)
        if query_match:
            params['query'] = query_match.group(1)

        return {
            "name": name,
            "parameters": params
        }

    async def generate_final_response(
        self,
        original_request: str,
        tool_results: Dict[str, Any],
        context: List[Dict]
    ) -> str:
        """ツール実行結果を基に最終応答を生成"""
        try:
            logger.info(f"Generating final response for request: {original_request}")
            logger.debug(f"Tool results: {tool_results}")
            logger.debug(f"Context length: {len(context) if context else 0}")

            # ツール結果を含むプロンプトを構築
            tool_summary = self._format_tool_results(tool_results)
            logger.debug(f"Tool summary: {tool_summary}")

            # メッセージリストを構築
            messages = [
                {"role": "system", "content":
                 "以下のツール実行結果を基に、ユーザーに分かりやすい応答を生成してください。\n"
                 "【重要ルール】\n"
                 "• 必ず1〜2文以内で簡潔に答える\n"
                 "• 応答構造: 結論を先に → 必要なら簡潔な補足\n"
                 "• ツールが返した結果をそのまま伝える（余計な解釈や説明を加えない）\n"
                 "• 技術的な詳細は省略し、自然な日本語で\n"
                 "• 「〜ですね」「〜ですよ」など柔らかい語尾を使う"}
            ]

            # コンテキストを追加（最新5件）
            if context:
                messages.extend(context[-5:])

            # リクエストと結果を追加（userメッセージ1つにまとめる）
            messages.append({
                "role": "user",
                "content": f"元のリクエスト: {original_request}\n\nツール実行結果:\n{tool_summary}\n\n上記の結果を1〜2文以内で簡潔に伝えてください。"
            })

            logger.debug(f"Sending {len(messages)} messages to LLM")
            response = await self._generate_with_fallback(messages)
            logger.info(f"Successfully generated final response: {response['content'][:100]}...")
            return response["content"]

        except Exception as e:
            logger.error(f"Failed to generate final response: {e}")
            logger.exception("Full traceback:")
            return "ツールを実行しましたが、結果の処理中にエラーが発生しました。"

    def _format_tool_results(self, tool_results: Dict[str, Any]) -> str:
        """ツール実行結果をフォーマット"""
        formatted_results = []

        for tool_name, result in tool_results.items():
            # メタデータキーはスキップ（_metadataサフィックス）
            if tool_name.endswith('_metadata'):
                continue

            # 結果が辞書型の場合、ユーザー向けメッセージを抽出
            if isinstance(result, dict):
                # "message"キーがあればそれを優先的に使用
                if "message" in result:
                    formatted_results.append(f"{tool_name}: {result['message']}")
                else:
                    # メッセージがない場合はJSON形式で表示
                    import json
                    formatted_results.append(f"{tool_name}: {json.dumps(result, ensure_ascii=False, indent=2)}")
            else:
                # 文字列などそのまま使えるデータ
                formatted_results.append(f"{tool_name}: {result}")

        return "\n".join(formatted_results)

    async def _generate_with_fallback(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """フォールバック機能付きでLLM生成を実行"""
        primary = self.config["primary_provider"]
        fallback = self.config["fallback_provider"]

        logger.info(f"Starting LLM generation with primary: {primary}, fallback: {fallback}")
        logger.debug(f"Available providers: {[name for name, p in self.providers.items() if p.is_available]}")

        # プライマリプロバイダーを試行
        if primary in self.providers and self.providers[primary].is_available:
            try:
                logger.info(f"Attempting generation with primary provider: {primary}")
                return await self.providers[primary].generate(messages, **kwargs)
            except Exception as e:
                logger.error(f"Primary provider {primary} failed: {e}")
                logger.exception("Full traceback for primary provider:")

        # フォールバックプロバイダーを試行
        if (self.config["auto_fallback"] and
            fallback and
            fallback in self.providers and
            self.providers[fallback].is_available):
            try:
                logger.info(f"Falling back to provider: {fallback}")
                return await self.providers[fallback].generate(messages, **kwargs)
            except Exception as e:
                logger.error(f"Fallback provider {fallback} failed: {e}")
                logger.exception("Full traceback for fallback provider:")

        # 利用可能な任意のプロバイダーを試行
        for name, provider in self.providers.items():
            if provider.is_available and name not in [primary, fallback]:
                try:
                    logger.info(f"Trying alternative provider: {name}")
                    return await provider.generate(messages, **kwargs)
                except Exception as e:
                    logger.error(f"Alternative provider {name} failed: {e}")
                    logger.exception("Full traceback for alternative provider:")

        logger.error("All LLM providers failed - no available providers or all attempts failed")
        raise RuntimeError("All LLM providers failed")

    def _convert_tools_to_openai_schema(self, tools: List[Dict]) -> List[Dict[str, Any]]:
        """ToolRegistryの定義をOpenAI toolsスキーマに変換"""
        if not tools:
            return []

        def param_to_schema(p: Dict[str, Any]) -> Dict[str, Any]:
            schema = {"type": p.get("type", "string")}
            if p.get("description"):
                schema["description"] = p["description"]
            if p.get("enum"):
                schema["enum"] = p["enum"]
            if p.get("default") is not None:
                schema["default"] = p["default"]
            return schema

        result = []
        for t in tools:
            params = t.get("parameters", [])
            properties = {p["name"]: param_to_schema(p) for p in params}
            required = [p["name"] for p in params if p.get("required")]

            parameters_schema = {
                "type": "object",
                "properties": properties,
                "additionalProperties": False,
            }
            if required:
                parameters_schema["required"] = required

            result.append({
                "type": "function",
                "function": {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": parameters_schema,
                }
            })

        return result

    async def get_status(self) -> Dict[str, Any]:
        """システム状態の取得"""
        provider_status = {}
        for name, provider in self.providers.items():
            provider_status[name] = provider.get_status()

        return {
            "initialized": self.is_initialized,
            "primary_provider": self.config["primary_provider"],
            "fallback_provider": self.config["fallback_provider"],
            "privacy_mode": self.config["privacy_mode"],
            "providers": provider_status
        }

    async def update_config(self, config: Dict[str, Any]):
        """設定の更新"""
        logger.info(f"Updating LLM config: {config}")

        old_config = self.config.copy()
        self.config.update(config)

        # モデルが変更された場合、該当プロバイダーを再初期化
        if "model" in config:
            provider_name = self.config.get("primary_provider")
            if provider_name and provider_name in self.providers:
                provider = self.providers[provider_name]
                if provider_name == "claude":
                    await provider.initialize({
                        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
                        "model": config["model"]
                    })
                elif provider_name == "openai":
                    await provider.initialize({
                        "openai_api_key": os.getenv("OPENAI_API_KEY"),
                        "model": config["model"]
                    })
                logger.info(f"Model updated to {config['model']} for provider {provider_name}")

        # プロバイダーが変更された場合は再初期化
        if (old_config.get("primary_provider") != self.config.get("primary_provider") or
            old_config.get("privacy_mode") != self.config.get("privacy_mode")):
            logger.info("Provider configuration changed, reinitializing...")
            await self.initialize()

    async def cleanup(self):
        """リソースのクリーンアップ"""
        logger.info("Cleaning up Hybrid LLM system...")

        self.providers.clear()
        self.is_initialized = False

        logger.info("Hybrid LLM system cleanup completed")
