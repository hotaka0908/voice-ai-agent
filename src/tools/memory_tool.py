"""
Memory Tool - メモリ管理ツール

ユーザーの情報を記憶・保存・検索するツール
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter


class MemoryTool(Tool):
    """メモリ管理を行うツール"""

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return "ユーザーの情報を記憶、保存、検索します"

    @property
    def category(self) -> str:
        return "utility"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="実行するアクション",
                required=True,
                enum=["save", "search", "list", "delete"]
            ),
            ToolParameter(
                name="key",
                type="string",
                description="保存・検索するキー（例：name, preference, schedule）",
                required=False
            ),
            ToolParameter(
                name="value",
                type="string",
                description="保存する値",
                required=False
            ),
            ToolParameter(
                name="query",
                type="string",
                description="検索クエリ",
                required=False
            )
        ]

    async def _initialize_impl(self):
        """メモリツールの初期化"""
        # 簡易的なメモリストレージ（実際のシステムではデータベースを使用）
        self.memory_storage = {}
        self.memory_file = "data/memory/user_memory.json"

        # 既存のメモリを読み込み
        try:
            import os
            os.makedirs("data/memory", exist_ok=True)

            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.memory_storage = json.load(f)
                logger.info(f"Loaded {len(self.memory_storage)} memory entries")
        except Exception as e:
            logger.warning(f"Failed to load memory file: {e}")
            self.memory_storage = {}

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """メモリ操作を実行"""
        try:
            action = parameters.get("action", "").lower()

            if action == "save":
                return await self._save_memory(parameters)
            elif action == "search":
                return await self._search_memory(parameters)
            elif action == "list":
                return await self._list_memory()
            elif action == "delete":
                return await self._delete_memory(parameters)
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error="サポートされていないアクションです"
                )

        except Exception as e:
            logger.error(f"Memory tool execution failed: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=f"メモリ操作に失敗しました: {str(e)}"
            )

    async def _save_memory(self, parameters: Dict[str, Any]) -> ToolResult:
        """情報を記憶に保存"""
        key = parameters.get("key", "")
        value = parameters.get("value", "")

        if not key or not value:
            return ToolResult(
                success=False,
                result=None,
                error="キーと値の両方を指定してください"
            )

        # メモリエントリを作成
        memory_entry = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "updated_count": self.memory_storage.get(key, {}).get("updated_count", 0) + 1
        }

        self.memory_storage[key] = memory_entry

        # ファイルに保存
        await self._persist_memory()

        return ToolResult(
            success=True,
            result=f"💾 記憶しました: {key} = {value}",
            metadata={"key": key, "value": value}
        )

    async def _search_memory(self, parameters: Dict[str, Any]) -> ToolResult:
        """記憶を検索"""
        query = parameters.get("query", "").lower()
        key = parameters.get("key", "").lower()

        if not query and not key:
            return ToolResult(
                success=False,
                result=None,
                error="検索クエリまたはキーを指定してください"
            )

        results = []

        # キーが指定されている場合は直接検索
        if key:
            if key in self.memory_storage:
                entry = self.memory_storage[key]
                results.append({
                    "key": key,
                    "value": entry["value"],
                    "timestamp": entry["timestamp"]
                })

        # クエリが指定されている場合は全文検索
        elif query:
            for mem_key, entry in self.memory_storage.items():
                if (query in mem_key.lower() or
                    query in entry["value"].lower()):
                    results.append({
                        "key": mem_key,
                        "value": entry["value"],
                        "timestamp": entry["timestamp"]
                    })

        if not results:
            return ToolResult(
                success=True,
                result="🔍 該当する記憶が見つかりませんでした",
                metadata={"query": query, "key": key}
            )

        # 結果を整形
        result_text = f"🧠 記憶検索結果 ({len(results)}件):\n\n"
        for result in results[:10]:  # 最大10件
            timestamp = datetime.fromisoformat(result["timestamp"]).strftime("%Y-%m-%d %H:%M")
            result_text += f"• {result['key']}: {result['value']} ({timestamp})\n"

        return ToolResult(
            success=True,
            result=result_text.strip(),
            metadata={"results_count": len(results)}
        )

    async def _list_memory(self) -> ToolResult:
        """すべての記憶をリスト表示"""
        if not self.memory_storage:
            return ToolResult(
                success=True,
                result="📋 保存されている記憶はありません"
            )

        result_text = f"📋 保存されている記憶 ({len(self.memory_storage)}件):\n\n"

        # 最新の記憶から表示
        sorted_entries = sorted(
            self.memory_storage.items(),
            key=lambda x: x[1]["timestamp"],
            reverse=True
        )

        for key, entry in sorted_entries[:20]:  # 最新20件
            timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%Y-%m-%d %H:%M")
            value_preview = entry["value"][:50] + "..." if len(entry["value"]) > 50 else entry["value"]
            result_text += f"• {key}: {value_preview} ({timestamp})\n"

        return ToolResult(
            success=True,
            result=result_text.strip(),
            metadata={"total_count": len(self.memory_storage)}
        )

    async def _delete_memory(self, parameters: Dict[str, Any]) -> ToolResult:
        """記憶を削除"""
        key = parameters.get("key", "")

        if not key:
            return ToolResult(
                success=False,
                result=None,
                error="削除するキーを指定してください"
            )

        if key not in self.memory_storage:
            return ToolResult(
                success=False,
                result=None,
                error=f"キー '{key}' は見つかりませんでした"
            )

        deleted_value = self.memory_storage[key]["value"]
        del self.memory_storage[key]

        # ファイルに保存
        await self._persist_memory()

        return ToolResult(
            success=True,
            result=f"🗑️ 記憶を削除しました: {key} = {deleted_value}",
            metadata={"key": key, "deleted_value": deleted_value}
        )

    async def _persist_memory(self):
        """メモリをファイルに永続化"""
        try:
            import os
            os.makedirs("data/memory", exist_ok=True)

            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory_storage, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to persist memory: {e}")

    async def store_personal_info(self, personal_info: Dict[str, Any]):
        """個人情報を保存"""
        logger.info(f"Storing personal information: {personal_info}")

        for key, value in personal_info.items():
            if value:  # 空の値は保存しない
                memory_entry = {
                    "value": str(value),
                    "timestamp": datetime.now().isoformat(),
                    "category": "personal_info",
                    "updated_count": self.memory_storage.get(f"personal_{key}", {}).get("updated_count", 0) + 1
                }

                self.memory_storage[f"personal_{key}"] = memory_entry

        # ファイルに保存
        await self._persist_memory()
        logger.info("Personal information stored successfully")

    async def get_personal_info(self) -> Dict[str, str]:
        """保存された個人情報を取得"""
        personal_info = {}

        for key, entry in self.memory_storage.items():
            if key.startswith("personal_") and entry.get("category") == "personal_info":
                # personal_ プレフィックスを除去してキー名を取得
                clean_key = key[9:]  # "personal_"を除去
                personal_info[clean_key] = entry["value"]

        return personal_info

    def format_personal_context(self) -> str:
        """個人情報をLLMのコンテキスト用に整形"""
        try:
            # 同期的に個人情報を取得
            personal_info = {}
            for key, entry in self.memory_storage.items():
                if key.startswith("personal_") and entry.get("category") == "personal_info":
                    clean_key = key[9:]  # "personal_"を除去
                    personal_info[clean_key] = entry["value"]

            if not personal_info:
                return ""

            context_parts = ["=== ユーザーの個人情報 ==="]

            if "name" in personal_info:
                context_parts.append(f"名前: {personal_info['name']}")
            if "age" in personal_info:
                context_parts.append(f"年齢: {personal_info['age']}歳")
            if "location" in personal_info:
                context_parts.append(f"居住地: {personal_info['location']}")
            if "occupation" in personal_info:
                context_parts.append(f"職業: {personal_info['occupation']}")
            if "hobbies" in personal_info:
                context_parts.append(f"趣味・興味: {personal_info['hobbies']}")

            context_parts.append("この情報を参考に、パーソナライズされた応答をしてください。")
            context_parts.append("=== ここまで個人情報 ===\n")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Failed to format personal context: {e}")
            return ""

    async def _cleanup_impl(self):
        """クリーンアップ時にメモリを保存"""
        await self._persist_memory()