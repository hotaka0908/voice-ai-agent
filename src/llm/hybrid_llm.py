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

        # モード別の基本指示
        if ai_mode == "auto":
            prompt_parts = [
                "あなたはパーソナライズされた音声AIアシスタントです（全自動モード）。",
                "ユーザーの個人情報や好み、過去の会話を考慮して応答してください。",
                "質問に親しみやすく端的に答えてください。",
                "",
                "🔥 全自動モードの重要な指示:",
                "- ユーザーの明示的な指示がなくても、会話の文脈から意図を推測し、必要なツールを積極的に使用してください",
                "- ユーザーの潜在的なニーズを先回りして予測し、プロアクティブに行動してください",
                "- 例: 「おはよう」→ 未読メールチェック、天気情報取得、今日の予定確認",
                "- 例: 「忙しい」→ 今日の重要なタスク確認、リマインダー設定",
                "- 例: 挨拶や雑談の際も、時間帯や文脈に応じて有用な情報を自動的に提供",
                "- 実行したアクションは必ずテーブルに記録されるので、積極的にツールを使用してください",
            ]
        else:  # assist mode
            prompt_parts = [
                "あなたはパーソナライズされた音声AIアシスタントです（アシストモード）。",
                "ユーザーの個人情報や好み、過去の会話を考慮して応答してください。",
                "質問に親しみやすく端的に答えてください。",
                "",
                "📋 アシストモードの重要な指示:",
                "- ユーザーの明示的な指示に従ってツールを使用してください",
                "- 指示がない場合は、情報を提供したり質問に答えたりしてください",
                "- 必要に応じて、ツールの使用を提案することはできますが、勝手に実行しないでください",
            ]

        # 個人情報があれば追加し、積極的に活用
        if memory_tool:
            personal_context = memory_tool.format_personal_context()
            if personal_context:
                prompt_parts.append("")  # 空行を追加
                prompt_parts.append(personal_context)
                prompt_parts.append("\n重要: 上記の個人情報を積極的に活用してパーソナライズされた応答をしてください。")
                prompt_parts.append("例えば、趣味に関連した話題、年齢に適した表現、居住地の特色などを考慮してください。")
        else:
            prompt_parts.append("個人情報が登録されていないため、一般的な応答をしてください。")

        # 利用可能なツール情報を追加
        if available_tools:
            prompt_parts.append("\n利用可能なツール:")
            for tool in available_tools:
                prompt_parts.append(f"- {tool['name']}: {tool['description']}")

                # Gmailツールの場合は詳細な使用例を追加（最優先）
                if tool['name'] == 'gmail':
                    prompt_parts.append("  🔥 Gmailツール（最優先）:")
                    prompt_parts.append("  メール、gmail、ジーメールという言葉が出た場合は必ずこのツールを使用してください")
                    prompt_parts.append("  - 最新メール取得: TOOL_CALL: {\"name\": \"gmail\", \"parameters\": {\"action\": \"list\", \"max_results\": 1}}")
                    prompt_parts.append("  - メール詳細読み取り: TOOL_CALL: {\"name\": \"gmail\", \"parameters\": {\"action\": \"read\", \"message_id\": \"メールID\"}}")
                    prompt_parts.append("  - 未読メール取得: TOOL_CALL: {\"name\": \"gmail\", \"parameters\": {\"action\": \"list\", \"query\": \"is:unread\"}}")
                    prompt_parts.append("  - メール返信: TOOL_CALL: {\"name\": \"gmail\", \"parameters\": {\"action\": \"reply\", \"message_id\": \"メールID\", \"body\": \"返信本文\"}}")
                    prompt_parts.append("  ")
                    prompt_parts.append("  🔥 返信処理の重要な指示:")
                    prompt_parts.append("  - 「〇〇と返信して」「〇〇て返信」という要求があった場合:")

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
                        prompt_parts.append(f"    最新のメールID: {latest_email_id} を使用して返信してください")
                        prompt_parts.append(f"    例: TOOL_CALL: {{\"name\": \"gmail\", \"parameters\": {{\"action\": \"reply\", \"message_id\": \"{latest_email_id}\", \"body\": \"ユーザーが指定した返信内容\"}}}}")
                    else:
                        prompt_parts.append("    まず最新のメール一覧を取得してからメールIDを使って返信してください")
                        prompt_parts.append("    例: 先にTOOL_CALL: {\"name\": \"gmail\", \"parameters\": {\"action\": \"list\", \"max_results\": 1}}")
                        prompt_parts.append("    次にTOOL_CALL: {\"name\": \"gmail\", \"parameters\": {\"action\": \"reply\", \"message_id\": \"取得したメールID\", \"body\": \"返信内容\"}}")

                    prompt_parts.append("  ⚠️ 重要: message_idには実際に取得したメールのIDを使用してください。「メールID」「メッセージID」等のプレースホルダー文字列は絶対に使用禁止です。")
                    prompt_parts.append("  - 返信内容はユーザーの指示に忠実に従い、適切な敬語を使用してください")

                # アラームツールの場合は詳細な使用例を追加
                if tool['name'] == 'alarm':
                    prompt_parts.append("  🔔 アラームツール:")
                    prompt_parts.append("  「アラームをセットして」「〇時に起こして」「〇時にリマインドして」等の要求があった場合は必ずこのツールを使用してください")
                    prompt_parts.append("  - アラーム設定: TOOL_CALL: {\"name\": \"alarm\", \"parameters\": {\"action\": \"set\", \"time\": \"HH:MM\", \"message\": \"読み上げメッセージ\", \"label\": \"アラーム\", \"repeat\": false}}")
                    prompt_parts.append("  - アラーム一覧: TOOL_CALL: {\"name\": \"alarm\", \"parameters\": {\"action\": \"list\"}}")
                    prompt_parts.append("  - アラーム削除: TOOL_CALL: {\"name\": \"alarm\", \"parameters\": {\"action\": \"delete\", \"alarm_id\": \"アラームID\"}}")
                    prompt_parts.append("  ")
                    prompt_parts.append("  🔥 アラーム設定の重要な指示:")
                    prompt_parts.append("  - ユーザーが時刻を指定した場合:")
                    prompt_parts.append("    例1: 「7時に起こして」→ time=\"07:00\", message=\"起きる時間です\"")
                    prompt_parts.append("    例2: \"14時半にアラーム\"→ time=\"14:30\", message=\"アラーム\"")
                    prompt_parts.append("    例3: \"18時にリマインドして\"→ time=\"18:00\", message=\"リマインダー\"")
                    prompt_parts.append("  - ユーザーが具体的なメッセージを指定した場合はそれを使用:")
                    prompt_parts.append("    例: 「7時に薬を飲むとリマインドして」→ message=\"薬を飲む時間です\"")
                    prompt_parts.append("  - 時刻は必ずHH:MM形式（24時間制）で指定してください")
                    prompt_parts.append("  ⚠️ 重要: アラーム設定後は「〇時にアラームを設定しました」と確認メッセージを返してください")

            prompt_parts.append(
                "\n重要: ツールを使用する場合は、必ず正確な形式で指示してください。"
                "\n実在しないアクションパラメータは使用せず、ツールの仕様に従ってください。"
                "\nGmailの内容確認には必ずgmailツールを使用し、推測や仮定の情報は提供しないでください。"
                "\n形式: TOOL_CALL: {\"name\": \"ツール名\", \"parameters\": {\"パラメータ\": \"値\"}}"
            )

        # 関連する記憶があれば追加
        if memories:
            prompt_parts.append("\n=== 関連する過去の情報 ===")
            for memory in memories[:3]:  # 最新3件まで
                prompt_parts.append(f"- {memory.get('content', '')}")
            prompt_parts.append("=== ここまで過去の情報 ===")
            prompt_parts.append("重要: 上記の過去の情報を参考にして、継続性のある会話を心がけてください。")

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
            # ツール結果を含むプロンプトを構築
            tool_summary = self._format_tool_results(tool_results)

            messages = [
                {"role": "system", "content":
                 "以下のツール実行結果を基に、ユーザーに分かりやすい応答を生成してください。"
                 "技術的な詳細は省略し、結果を自然な日本語で説明してください。"},
                *context[-5:],  # 最新5件のコンテキスト
                {"role": "user", "content": f"元のリクエスト: {original_request}"},
                {"role": "assistant", "content": f"ツール実行結果:\n{tool_summary}"},
                {"role": "user", "content": "上記の結果を基に、分かりやすく回答してください。"}
            ]

            response = await self._generate_with_fallback(messages)
            return response["content"]

        except Exception as e:
            logger.error(f"Failed to generate final response: {e}")
            return "ツールを実行しましたが、結果の処理中にエラーが発生しました。"

    def _format_tool_results(self, tool_results: Dict[str, Any]) -> str:
        """ツール実行結果をフォーマット"""
        formatted_results = []

        for tool_name, result in tool_results.items():
            formatted_results.append(f"{tool_name}: {result}")

        return "\n".join(formatted_results)

    async def _generate_with_fallback(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """フォールバック機能付きでLLM生成を実行"""
        primary = self.config["primary_provider"]
        fallback = self.config["fallback_provider"]

        # プライマリプロバイダーを試行
        if primary in self.providers and self.providers[primary].is_available:
            try:
                logger.debug(f"Attempting generation with primary provider: {primary}")
                return await self.providers[primary].generate(messages, **kwargs)
            except Exception as e:
                logger.warning(f"Primary provider {primary} failed: {e}")

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

        # 利用可能な任意のプロバイダーを試行
        for name, provider in self.providers.items():
            if provider.is_available and name not in [primary, fallback]:
                try:
                    logger.info(f"Trying alternative provider: {name}")
                    return await provider.generate(messages, **kwargs)
                except Exception as e:
                    logger.warning(f"Alternative provider {name} failed: {e}")

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
