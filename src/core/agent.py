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
from src.core.rule_processor import RuleProcessor


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
        self.rule_processor: Optional[RuleProcessor] = None
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
            self.rule_processor = RuleProcessor()

            # 初期化の実行
            await asyncio.gather(
                self.stt.initialize(),
                self.tts.initialize(),
                self.llm.initialize(),
                self.memory.initialize(),
                self.tools.initialize(),
                self.context.initialize(),
                self.rule_processor.initialize()
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

            # 2. ルールベース処理をまず試行
            # メモリツールを取得
            memory_tool = self.tools.get_tool("memory")

            rule_response = await self.rule_processor.process_input(
                text,
                context=self.context.get_context(),
                memory_tool=memory_tool
            )

            # ルールにマッチし、即時応答がある場合はそのまま返す
            if rule_response and rule_response.get("is_final"):
                final_response = rule_response.get("response", "")

                # コンテキストに追加
                await self.context.add_assistant_message(final_response)

                # 記憶への保存
                await self.memory.store_interaction(text, final_response)

                # 会話履歴を保存（性格分析用）
                if memory_tool:
                    await memory_tool.save_conversation(text, final_response)

                # 音声合成
                audio_url = await self.tts.synthesize(final_response)

                return {
                    "text": final_response,
                    "audio_url": audio_url,
                    "tool_results": [],
                    "rule_used": rule_response.get("rule_name"),
                    "timestamp": await self._get_current_timestamp()
                }

            # ルールにマッチし、ツール提案がある場合は先に実行（Gmail等）
            if rule_response and not rule_response.get("is_final") and rule_response.get("tool_calls"):
                tool_results = await self._execute_tools(rule_response["tool_calls"])

                # Gmailツールの結果からメールIDを抽出してコンテキストに保存
                await self._extract_and_store_email_ids(tool_results)

                # 単純にツール結果を応答として返す（フォーマット済み文字列想定）
                combined_texts = []
                for name, result in tool_results.items():
                    if isinstance(result, str):
                        combined_texts.append(result)
                    else:
                        combined_texts.append(str(result))
                final_response = "\n\n".join([t for t in combined_texts if t]) or "処理が完了しました。"

                await self.context.add_assistant_message(final_response)
                await self.memory.store_interaction(text, final_response)

                # 会話履歴を保存（性格分析用）
                if memory_tool:
                    await memory_tool.save_conversation(text, final_response)

                audio_url = await self.tts.synthesize(final_response)

                return {
                    "text": final_response,
                    "audio_url": audio_url,
                    "tool_results": rule_response.get("tool_calls", []),
                    "rule_used": rule_response.get("rule_name"),
                    "timestamp": await self._get_current_timestamp()
                }

            # 3. ルールにマッチしなかった場合はAI処理
            # 記憶からの関連情報取得
            relevant_memories = await self.memory.search_relevant(text)

            # 現在のAIモードを取得
            ai_mode = await memory_tool.get_ai_mode() if memory_tool else "assist"
            logger.info(f"Current AI mode: {ai_mode}")

            # 4. LLMで意図理解とツール選択
            # メモリツールは既に取得済み

            llm_response = await self.llm.process_with_tools(
                text=text,
                context=self.context.get_context(),
                memories=relevant_memories,
                available_tools=self.tools.get_available_tools(),
                memory_tool=memory_tool,
                context_manager=self.context,
                ai_mode=ai_mode
            )

            # 5. ツールの実行（必要な場合）
            logger.debug(f"LLM response tool_calls: {llm_response.get('tool_calls')}")
            if llm_response.get("tool_calls"):
                logger.info(f"Executing {len(llm_response['tool_calls'])} tools")

                # 全自動モードの場合、テーブルタスクを作成
                if ai_mode == "auto" and memory_tool:
                    task_title = f"自動実行: {text[:30]}..."
                    task_content = f"ユーザー入力: {text}\nツール: {', '.join([tc.get('name', '') for tc in llm_response['tool_calls']])}"
                    table_task = await memory_tool.add_table_task(
                        title=task_title,
                        content=task_content,
                        status="processing"
                    )
                    task_id = table_task.get("id")
                    logger.info(f"Created table task for auto mode: {task_id}")
                else:
                    task_id = None

                tool_results = await self._execute_tools(llm_response["tool_calls"])
                logger.debug(f"Tool execution results: {tool_results}")

                # Gmailツールの結果からメールIDを抽出してコンテキストに保存
                await self._extract_and_store_email_ids(tool_results)

                # ツール結果を含めて再度LLM処理
                final_response = await self.llm.generate_final_response(
                    original_request=text,
                    tool_results=tool_results,
                    context=self.context.get_context()
                )

                # 全自動モードの場合、テーブルタスクを完了に更新
                if ai_mode == "auto" and memory_tool and task_id:
                    result_summary = final_response[:100] + "..." if len(final_response) > 100 else final_response
                    await memory_tool.update_table_task(
                        task_id=task_id,
                        status="completed",
                        result=result_summary
                    )
                    logger.info(f"Updated table task to completed: {task_id}")
            else:
                logger.warning("No tool calls found in LLM response - AI may generate fake content")
                final_response = llm_response.get("response", "")

            # 6. 応答をコンテキストに追加
            await self.context.add_assistant_message(final_response)

            # 7. 記憶への保存
            await self.memory.store_interaction(text, final_response)

            # 会話履歴を保存（性格分析用）
            if memory_tool:
                await memory_tool.save_conversation(text, final_response)

            # 8. 音声合成
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

            logger.debug(f"Processing tool call: {tool_name} with params: {tool_params}")

            # Gmailツールのプレースホルダー置換処理
            if tool_name == "gmail" and tool_params.get("message_id"):
                logger.info(f"Gmail tool detected with message_id: {tool_params.get('message_id')}")
                original_params = tool_params.copy()
                tool_params = await self._replace_placeholder_email_id(tool_params)
                logger.info(f"Placeholder replacement: {original_params} -> {tool_params}")

            try:
                logger.info(f"Executing tool: {tool_name} with final params: {tool_params}")
                result = await self.tools.execute_tool(tool_name, tool_params)

                # ToolResultオブジェクトの場合は結果を抽出
                if hasattr(result, 'result'):
                    results[tool_name] = result.result
                    logger.debug(f"Tool {tool_name} result: {result.result}")

                    # メタデータも保存（ID抽出用）
                    if hasattr(result, 'metadata') and result.metadata:
                        results[f"{tool_name}_metadata"] = result.metadata
                        logger.debug(f"Tool {tool_name} metadata: {result.metadata}")
                else:
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
                "tools": await self.tools.get_status()
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
        if self.rule_processor:
            cleanup_tasks.append(self.rule_processor.cleanup())

        await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self.is_initialized = False
        logger.info("Voice Agent cleanup completed")

    async def _extract_and_store_email_ids(self, tool_results: Dict[str, Any]):
        """Gmailツール結果からメールIDを抽出してコンテキストに保存"""
        try:
            gmail_result = tool_results.get("gmail")
            gmail_metadata = tool_results.get("gmail_metadata")

            logger.debug(f"Gmail tool result for ID extraction: {gmail_result}")
            logger.debug(f"Gmail metadata: {gmail_metadata}")
            logger.debug(f"Tool results keys: {list(tool_results.keys())}")

            # まず、メタデータからメールIDを確認
            if gmail_metadata and isinstance(gmail_metadata, dict):
                latest_email_id = gmail_metadata.get("latest_email_id")
                if latest_email_id:
                    self.context.set_latest_email_id(latest_email_id)
                    logger.info(f"✅ Stored latest email ID from metadata: {latest_email_id}")
                    return

            # メタデータから取得できない場合は従来の方法
            if not gmail_result or not isinstance(gmail_result, str):
                logger.debug(f"Gmail result is not a string or is empty. Type: {type(gmail_result)}")
                return

            # メール一覧結果からIDを抽出
            import re
            id_pattern = r'ID:\s*([a-zA-Z0-9]+)'
            matches = re.findall(id_pattern, gmail_result)
            logger.debug(f"Regex matches found: {matches}")

            if matches:
                # 最初のメールIDを保存（最新のメール）
                email_id = matches[0]
                self.context.set_latest_email_id(email_id)
                logger.info(f"✅ Stored latest email ID: {email_id}")
            else:
                logger.warning(f"❌ No email IDs found in Gmail result: {gmail_result[:200]}")

        except Exception as e:
            logger.error(f"Failed to extract email ID: {e}")

    async def _replace_placeholder_email_id(self, tool_params: Dict[str, Any]) -> Dict[str, Any]:
        """GmailツールのプレースホルダーメールIDを実際のIDに置換"""
        logger.info(f"_replace_placeholder_email_id called with params: {tool_params}")

        placeholder_patterns = ["メールID", "メッセージID", "email_id", "message_id_placeholder"]

        # パラメータをコピーして変更
        updated_params = tool_params.copy()
        message_id = updated_params.get("message_id")

        logger.info(f"Checking message_id: '{message_id}' against patterns: {placeholder_patterns}")

        if message_id in placeholder_patterns:
            # コンテキストから最新のメールIDを取得
            actual_email_id = self.context.get_latest_email_id()
            logger.info(f"Found placeholder '{message_id}', available email ID from context: {actual_email_id}")

            if actual_email_id:
                updated_params["message_id"] = actual_email_id
                logger.info(f"✅ Replaced placeholder '{message_id}' with actual email ID: {actual_email_id}")
            else:
                logger.warning(f"❌ No stored email ID found to replace placeholder '{message_id}'")
        else:
            logger.debug(f"ℹ️  Message ID '{message_id}' is not a placeholder, using as-is")

        logger.info(f"Final updated params: {updated_params}")
        return updated_params

    async def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプをISO形式で返す"""
        return datetime.now().isoformat()
