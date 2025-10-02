"""
Calendar Tool - カレンダー管理ツール

イベントの作成、取得、削除などを行うツール
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter


class CalendarTool(Tool):
    """カレンダー管理ツール"""

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def description(self) -> str:
        return "カレンダーイベントの作成、取得、削除を行います"

    @property
    def category(self) -> str:
        return "productivity"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="実行するアクション（create, list, delete）",
                required=True,
                enum=["create", "list", "delete"]
            ),
            ToolParameter(
                name="title",
                type="string",
                description="イベントのタイトル",
                required=False
            ),
            ToolParameter(
                name="start_time",
                type="string",
                description="開始時刻（ISO 8601形式）",
                required=False
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="終了時刻（ISO 8601形式）",
                required=False
            ),
            ToolParameter(
                name="description",
                type="string",
                description="イベントの説明",
                required=False
            ),
            ToolParameter(
                name="event_id",
                type="string",
                description="イベントID（削除時に使用）",
                required=False
            )
        ]

    async def _initialize_impl(self):
        """カレンダーツールの初期化"""
        # メモリ内にイベントを保存（実際の実装ではデータベースやGoogle Calendar APIを使用）
        self.events = []
        self.next_id = 1
        logger.info("Calendar tool initialized")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """カレンダー操作を実行"""
        try:
            action = parameters.get("action")

            if action == "create":
                return await self._create_event(parameters)
            elif action == "list":
                return await self._list_events(parameters)
            elif action == "delete":
                return await self._delete_event(parameters)
            else:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"不明なアクション: {action}"
                )

        except Exception as e:
            logger.error(f"Calendar tool error: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e)
            )

    async def _create_event(self, parameters: Dict[str, Any]) -> ToolResult:
        """イベントを作成"""
        title = parameters.get("title", "無題のイベント")
        start_time = parameters.get("start_time")
        end_time = parameters.get("end_time")
        description = parameters.get("description", "")

        event = {
            "id": str(self.next_id),
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "created_at": datetime.now().isoformat()
        }

        self.events.append(event)
        self.next_id += 1

        return ToolResult(
            success=True,
            data={
                "message": f"イベント「{title}」を作成しました",
                "event": event
            }
        )

    async def _list_events(self, parameters: Dict[str, Any]) -> ToolResult:
        """イベント一覧を取得"""
        return ToolResult(
            success=True,
            data={
                "events": self.events,
                "count": len(self.events)
            }
        )

    async def _delete_event(self, parameters: Dict[str, Any]) -> ToolResult:
        """イベントを削除"""
        event_id = parameters.get("event_id")

        if not event_id:
            return ToolResult(
                success=False,
                data={},
                error="event_idが必要です"
            )

        # イベントを検索して削除
        for i, event in enumerate(self.events):
            if event["id"] == event_id:
                deleted_event = self.events.pop(i)
                return ToolResult(
                    success=True,
                    data={
                        "message": f"イベント「{deleted_event['title']}」を削除しました",
                        "event": deleted_event
                    }
                )

        return ToolResult(
            success=False,
            data={},
            error=f"ID {event_id} のイベントが見つかりません"
        )
