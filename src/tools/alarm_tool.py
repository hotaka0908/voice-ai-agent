"""
Alarm Tool - アラーム管理ツール

アラームの設定、取得、削除などを行うツール
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter


class AlarmTool(Tool):
    """アラーム管理ツール"""

    @property
    def name(self) -> str:
        return "alarm"

    @property
    def description(self) -> str:
        return "アラームの設定、削除を行います。"

    @property
    def category(self) -> str:
        return "productivity"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="実行するアクション（set, list, delete）",
                required=True,
                enum=["set", "list", "delete"]
            ),
            ToolParameter(
                name="time",
                type="string",
                description="アラーム時刻（HH:MM形式）",
                required=False
            ),
            ToolParameter(
                name="label",
                type="string",
                description="アラームのラベル",
                required=False
            ),
            ToolParameter(
                name="message",
                type="string",
                description="読み上げるメッセージ",
                required=False
            ),
            ToolParameter(
                name="repeat",
                type="boolean",
                description="繰り返し設定",
                required=False,
                default=False
            ),
            ToolParameter(
                name="alarm_id",
                type="string",
                description="アラームID（削除時に使用）",
                required=False
            )
        ]

    async def _initialize_impl(self):
        """アラームツールの初期化"""
        # メモリ内にアラームを保存
        self.alarms = []
        self.next_id = 1
        logger.info("Alarm tool initialized")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """アラーム操作を実行"""
        try:
            action = parameters.get("action")

            if action == "set":
                return await self._set_alarm(parameters)
            elif action == "list":
                return await self._list_alarms(parameters)
            elif action == "delete":
                return await self._delete_alarm(parameters)
            else:
                return ToolResult(
                    success=False,
                    result={},
                    error=f"不明なアクション: {action}"
                )

        except Exception as e:
            logger.error(f"Alarm tool error: {e}")
            return ToolResult(
                success=False,
                result={},
                error=str(e)
            )

    async def _set_alarm(self, parameters: Dict[str, Any]) -> ToolResult:
        """アラームを設定"""
        time_str = parameters.get("time")
        label = parameters.get("label", "アラーム")
        message = parameters.get("message", "")
        repeat = parameters.get("repeat", False)

        if not time_str:
            return ToolResult(
                success=False,
                result={},
                error="時刻の指定が必要です"
            )

        alarm = {
            "id": str(self.next_id),
            "time": time_str,
            "label": label,
            "message": message,
            "repeat": repeat,
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }

        self.alarms.append(alarm)
        self.next_id += 1

        return ToolResult(
            success=True,
            result={
                "message": f"{time_str}に「{label}」のアラームを設定しました",
                "alarm": alarm
            }
        )

    async def _list_alarms(self, parameters: Dict[str, Any]) -> ToolResult:
        """アラーム一覧を取得"""
        return ToolResult(
            success=True,
            result={
                "alarms": self.alarms,
                "count": len(self.alarms)
            }
        )

    async def _delete_alarm(self, parameters: Dict[str, Any]) -> ToolResult:
        """アラームを削除"""
        alarm_id = parameters.get("alarm_id")

        if not alarm_id:
            return ToolResult(
                success=False,
                result={},
                error="alarm_idが必要です"
            )

        # アラームを検索して削除
        for i, alarm in enumerate(self.alarms):
            if alarm["id"] == alarm_id:
                deleted_alarm = self.alarms.pop(i)
                return ToolResult(
                    success=True,
                    result={
                        "message": f"「{deleted_alarm['label']}」({deleted_alarm['time']})のアラームを削除しました",
                        "alarm": deleted_alarm
                    }
                )

        return ToolResult(
            success=False,
            result={},
            error=f"ID {alarm_id} のアラームが見つかりません"
        )
