"""
Dummy Tools - 未実装ツールのプレースホルダー

実装予定のツールをダミーとして登録
"""

from typing import Dict, Any, List
from loguru import logger

from src.core.tool_base import Tool, ToolParameter, ToolResult


class AirconTool(Tool):
    """エアコン制御ツール（未実装）"""

    @property
    def name(self) -> str:
        return "aircon"

    @property
    def description(self) -> str:
        return "エアコンの操作を行います。（準備中）"

    @property
    def category(self) -> str:
        return "smart_home"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="実行する操作（on/off/temp）",
                required=True,
                enum=["on", "off", "temp"]
            ),
            ToolParameter(
                name="temperature",
                type="number",
                description="設定温度（temp操作時）",
                required=False
            )
        ]

    async def _initialize_impl(self):
        """初期化処理"""
        logger.info("AirconTool initialized (dummy)")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """実行処理"""
        return ToolResult(
            success=False,
            result="エアコン機能は準備中です。",
            error="Not implemented"
        )


class LightTool(Tool):
    """照明制御ツール（未実装）"""

    @property
    def name(self) -> str:
        return "light"

    @property
    def description(self) -> str:
        return "リビングの照明を操作します。（準備中）"

    @property
    def category(self) -> str:
        return "smart_home"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="実行する操作（on/off/dim）",
                required=True,
                enum=["on", "off", "dim"]
            ),
            ToolParameter(
                name="brightness",
                type="number",
                description="明るさ（0-100、dim操作時）",
                required=False
            )
        ]

    async def _initialize_impl(self):
        """初期化処理"""
        logger.info("LightTool initialized (dummy)")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """実行処理"""
        return ToolResult(
            success=False,
            result="照明機能は準備中です。",
            error="Not implemented"
        )


class TaxiTool(Tool):
    """タクシー配車ツール（未実装）"""

    @property
    def name(self) -> str:
        return "taxi"

    @property
    def description(self) -> str:
        return "タクシーの配車を行います。（準備中）"

    @property
    def category(self) -> str:
        return "transportation"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="pickup_location",
                type="string",
                description="乗車場所",
                required=True
            ),
            ToolParameter(
                name="destination",
                type="string",
                description="目的地",
                required=False
            )
        ]

    async def _initialize_impl(self):
        """初期化処理"""
        logger.info("TaxiTool initialized (dummy)")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """実行処理"""
        return ToolResult(
            success=False,
            result="タクシー配車機能は準備中です。",
            error="Not implemented"
        )


class RobotTool(Tool):
    """ロボット制御ツール（未実装）"""

    @property
    def name(self) -> str:
        return "robot"

    @property
    def description(self) -> str:
        return "ロボットを操作します。（準備中）"

    @property
    def category(self) -> str:
        return "smart_home"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="command",
                type="string",
                description="実行するコマンド",
                required=True
            )
        ]

    async def _initialize_impl(self):
        """初期化処理"""
        logger.info("RobotTool initialized (dummy)")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """実行処理"""
        return ToolResult(
            success=False,
            result="ロボット機能は準備中です。",
            error="Not implemented"
        )
