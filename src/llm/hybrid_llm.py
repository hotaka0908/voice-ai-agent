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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
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
        available_tools: List[Dict]
    ) -> Dict[str, Any]:
        """
        ツール使用を含む複雑な処理

        Args:
            text: ユーザーの入力テキスト
            context: 会話コンテキスト
            memories: 関連する記憶
            available_tools: 利用可能なツール

        Returns:
            処理結果（応答テキスト、ツール呼び出し等）
        """
        if not self.is_initialized:
            raise RuntimeError("HybridLLM not initialized")

        try:
            # システムプロンプトの構築
            system_prompt = self._build_system_prompt(available_tools, memories)

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
            tool_calls = response.get("tool_calls") or self._parse_tool_calls(response.get("content", ""))

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

    def _build_system_prompt(self, available_tools: List[Dict], memories: List[Dict]) -> str:
        """システムプロンプトを構築"""
        prompt_parts = [
            "あなたは簡潔で効率的な音声AIアシスタントです。",
            "ユーザーの質問に1-2文で端的に答えてください。",
            "長い説明や詳細な解説は避け、必要な情報のみを提供してください。",
            "自然で親しみやすい口調を保ちつつ、回答は短く簡潔にしてください。"
        ]

        # 利用可能なツール情報を追加
        if available_tools:
            prompt_parts.append("\n利用可能なツール:")
            for tool in available_tools:
                prompt_parts.append(f"- {tool['name']}: {tool['description']}")

            prompt_parts.append(
                "\nツールを使用する場合は、以下の形式で指示してください:\n"
                "TOOL_CALL: {\"name\": \"ツール名\", \"parameters\": {\"パラメータ\": \"値\"}}"
            )

        # 関連する記憶があれば追加
        if memories:
            prompt_parts.append("\n関連する過去の情報:")
            for memory in memories[:3]:  # 最新3件まで
                prompt_parts.append(f"- {memory.get('content', '')}")

        return "\n".join(prompt_parts)

    def _parse_tool_calls(self, content: str) -> List[Dict]:
        """応答からツール呼び出しを解析"""
        tool_calls = []

        # TOOL_CALL: {...} パターンを検索
        import re
        pattern = r'TOOL_CALL:\s*({.*?})'
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            try:
                tool_data = json.loads(match.strip())
                if "name" in tool_data:
                    tool_calls.append(tool_data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call: {match}")

        return tool_calls

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
