"""
Voice Agent - メインエージェントクラス

音声処理、自然言語理解、ツール実行を統合する中心的なクラス
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from src.audio.speech_to_text import SpeechToText
from src.audio.text_to_speech import TextToSpeech
from src.llm.hybrid_llm import HybridLLM
from src.memory.personal_memory import PersonalMemory
from src.tools.tool_registry import ToolRegistry
from src.core.context_manager import ContextManager


class VoiceAgent:
    """
    音声AIエージェントのメインクラス

    音声入力を受け取り、自然言語理解、ツール実行、応答生成を行う
    """

    def __init__(self):
        self.stt: Optional[SpeechToText] = None
        self.tts: Optional[TextToSpeech] = None
        self.llm: Optional[HybridLLM] = None
        self.memory: Optional[PersonalMemory] = None
        self.tools: Optional[ToolRegistry] = None
        self.context: Optional[ContextManager] = None
        self.is_initialized = False

    async def initialize(self):
        """エージェントの初期化"""
        try:
            logger.info("Initializing Voice Agent...")

            # 各コンポーネントの初期化
            self.stt = SpeechToText()
            self.tts = TextToSpeech()
            self.llm = HybridLLM()
            self.memory = PersonalMemory()
            self.tools = ToolRegistry()
            self.context = ContextManager()

            # 初期化の実行
            await asyncio.gather(
                self.stt.initialize(),
                self.tts.initialize(),
                self.llm.initialize(),
                self.memory.initialize(),
                self.tools.initialize(),
                self.context.initialize()
            )

            self.is_initialized = True
            logger.info("Voice Agent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Voice Agent: {e}")
            raise

    async def process_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """
        音声データを処理して応答を生成

        Args:
            audio_data: 音声データ（WAVバイト）

        Returns:
            処理結果（テキスト、音声URL等）
        """
        if not self.is_initialized:
            raise RuntimeError("Voice Agent not initialized")

        try:
            # 1. 音声をテキストに変換
            logger.debug("Converting speech to text...")
            text = await self.stt.transcribe(audio_data)

            if not text.strip():
                return {"error": "音声を認識できませんでした"}

            logger.info(f"Recognized: {text}")

            # 2. テキストを処理
            text_response = await self.process_text(text)

            # 3. 認識されたテキストも含めて返す
            text_response["user_text"] = text
            return text_response

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {"error": "音声処理中にエラーが発生しました"}

    async def process_text(self, text: str) -> Dict[str, Any]:
        """
        テキストを処理して応答を生成

        Args:
            text: 入力テキスト

        Returns:
            処理結果
        """
        if not self.is_initialized:
            raise RuntimeError("Voice Agent not initialized")

        try:
            # 1. コンテキストの更新
            await self.context.add_user_message(text)

            # 2. 記憶からの関連情報取得
            relevant_memories = await self.memory.search_relevant(text)

            # 3. LLMで意図理解とツール選択
            llm_response = await self.llm.process_with_tools(
                text=text,
                context=self.context.get_context(),
                memories=relevant_memories,
                available_tools=self.tools.get_available_tools()
            )

            # 4. ツールの実行（必要な場合）
            if llm_response.get("tool_calls"):
                tool_results = await self._execute_tools(llm_response["tool_calls"])

                # ツール結果を含めて再度LLM処理
                final_response = await self.llm.generate_final_response(
                    original_request=text,
                    tool_results=tool_results,
                    context=self.context.get_context()
                )
            else:
                final_response = llm_response.get("response", "")

            # 5. 応答をコンテキストに追加
            await self.context.add_assistant_message(final_response)

            # 6. 記憶への保存
            await self.memory.store_interaction(text, final_response)

            # 7. 音声合成
            audio_url = await self.tts.synthesize(final_response)

            return {
                "text": final_response,
                "audio_url": audio_url,
                "tool_results": llm_response.get("tool_calls", []),
                "timestamp": await self._get_current_timestamp()
            }

        except Exception as e:
            logger.error(f"Error processing text: {e}")
            return {"error": "処理中にエラーが発生しました"}

    async def _execute_tools(self, tool_calls: list) -> Dict[str, Any]:
        """ツールを実行して結果を取得"""
        results = {}

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_params = tool_call.get("parameters", {})

            try:
                logger.info(f"Executing tool: {tool_name}")
                result = await self.tools.execute_tool(tool_name, tool_params)
                results[tool_name] = result
                logger.debug(f"Tool {tool_name} result: {result}")

            except Exception as e:
                logger.error(f"Tool {tool_name} execution failed: {e}")
                results[tool_name] = f"エラーが発生しました: {str(e)}"

        return results

    async def get_status(self) -> Dict[str, Any]:
        """システム状態の取得"""
        if not self.is_initialized:
            return {"status": "not_initialized"}

        return {
            "status": "ready",
            "components": {
                "stt": await self.stt.get_status(),
                "tts": await self.tts.get_status(),
                "llm": await self.llm.get_status(),
                "memory": await self.memory.get_status(),
                "tools": self.tools.get_status()
            }
        }

    async def update_config(self, config: Dict[str, Any]):
        """設定の更新"""
        logger.info(f"Updating configuration: {config}")

        if "llm" in config:
            await self.llm.update_config(config["llm"])
        if "tts" in config:
            await self.tts.update_config(config["tts"])
        if "memory" in config:
            await self.memory.update_config(config["memory"])

    async def cleanup(self):
        """リソースのクリーンアップ"""
        if not self.is_initialized:
            return

        logger.info("Cleaning up Voice Agent...")

        # 各コンポーネントのクリーンアップ
        cleanup_tasks = []
        if self.stt:
            cleanup_tasks.append(self.stt.cleanup())
        if self.tts:
            cleanup_tasks.append(self.tts.cleanup())
        if self.llm:
            cleanup_tasks.append(self.llm.cleanup())
        if self.memory:
            cleanup_tasks.append(self.memory.cleanup())
        if self.tools:
            cleanup_tasks.append(self.tools.cleanup())

        await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self.is_initialized = False
        logger.info("Voice Agent cleanup completed")

    async def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプをISO形式で返す"""
        return datetime.now().isoformat()