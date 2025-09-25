"""
Tool Registry - ツール管理システム

各種ツールの登録、管理、実行を行うシステム
"""

import asyncio
from typing import Dict, Any, List, Optional, Type
from loguru import logger

from src.core.tool_base import Tool, ToolResult


class ToolRegistry:
    """
    ツールの登録・管理・実行を行うクラス

    各種ツールを動的に登録し、実行時に適切なツールを選択して実行する
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.tool_classes: Dict[str, Type[Tool]] = {}
        self.is_initialized = False

    async def initialize(self):
        """ツールレジストリの初期化"""
        try:
            logger.info("Initializing Tool Registry...")

            # 基本ツールの自動登録
            await self._register_built_in_tools()

            # 各ツールの初期化
            initialization_tasks = []
            for tool_name, tool_instance in self.tools.items():
                task = self._initialize_tool(tool_name, tool_instance)
                initialization_tasks.append(task)

            results = await asyncio.gather(*initialization_tasks, return_exceptions=True)

            # 初期化に失敗したツールを除去
            failed_tools = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    tool_name = list(self.tools.keys())[i]
                    logger.error(f"Failed to initialize tool {tool_name}: {result}")
                    failed_tools.append(tool_name)

            for tool_name in failed_tools:
                del self.tools[tool_name]

            successful_tools = len(self.tools)
            logger.info(f"Tool Registry initialized with {successful_tools} tools")
            self.is_initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Tool Registry: {e}")
            raise

    async def _register_built_in_tools(self):
        """組み込みツールの登録"""
        try:
            # 基本ツールを動的にインポート・登録
            from src.tools.weather_tool import WeatherTool
            from src.tools.time_tool import TimeTool
            from src.tools.calculator_tool import CalculatorTool
            from src.tools.memory_tool import MemoryTool
            from src.tools.search_tool import SearchTool

            built_in_tools = [
                WeatherTool(),
                TimeTool(),
                CalculatorTool(),
                MemoryTool(),
                SearchTool(),
            ]

            for tool in built_in_tools:
                await self.register_tool(tool)

        except ImportError as e:
            logger.warning(f"Some built-in tools not available: {e}")
        except Exception as e:
            logger.error(f"Failed to register built-in tools: {e}")

    async def _initialize_tool(self, tool_name: str, tool_instance: Tool):
        """個別ツールの初期化"""
        try:
            await tool_instance.initialize()
            logger.debug(f"Tool {tool_name} initialized successfully")
        except Exception as e:
            logger.error(f"Tool {tool_name} initialization failed: {e}")
            raise

    async def register_tool(self, tool: Tool):
        """
        ツールを登録

        Args:
            tool: 登録するツールインスタンス
        """
        try:
            tool_name = tool.name
            if tool_name in self.tools:
                logger.warning(f"Tool {tool_name} already registered, replacing")

            self.tools[tool_name] = tool
            self.tool_classes[tool_name] = type(tool)

            logger.info(f"Tool registered: {tool_name}")

        except Exception as e:
            logger.error(f"Failed to register tool {tool.name}: {e}")
            raise

    async def unregister_tool(self, tool_name: str):
        """
        ツールの登録を解除

        Args:
            tool_name: 登録解除するツール名
        """
        try:
            if tool_name not in self.tools:
                logger.warning(f"Tool {tool_name} not found")
                return

            # ツールのクリーンアップ
            tool = self.tools[tool_name]
            await tool.cleanup()

            # レジストリから削除
            del self.tools[tool_name]
            del self.tool_classes[tool_name]

            logger.info(f"Tool unregistered: {tool_name}")

        except Exception as e:
            logger.error(f"Failed to unregister tool {tool_name}: {e}")

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        ツールを実行

        Args:
            tool_name: 実行するツール名
            parameters: ツールのパラメータ

        Returns:
            ツールの実行結果
        """
        if not self.is_initialized:
            raise RuntimeError("Tool Registry not initialized")

        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        tool = self.tools[tool_name]

        try:
            logger.info(f"Executing tool: {tool_name}")
            logger.debug(f"Tool parameters: {parameters}")

            # パラメータの検証
            if not await tool.validate_parameters(parameters):
                raise ValueError(f"Invalid parameters for tool {tool_name}")

            # 危険なツールの場合は確認
            if tool.is_dangerous:
                logger.warning(f"Executing dangerous tool: {tool_name}")

            # ツールの実行
            result = await tool.execute(parameters)

            if isinstance(result, ToolResult):
                if result.success:
                    logger.info(f"Tool {tool_name} executed successfully")
                    return result.result
                else:
                    logger.error(f"Tool {tool_name} execution failed: {result.error}")
                    return result.error or "ツールの実行に失敗しました"
            else:
                # 後方互換性のため、ToolResult以外も受け入れる
                logger.info(f"Tool {tool_name} executed successfully")
                return result

        except Exception as e:
            logger.error(f"Tool {tool_name} execution error: {e}")
            return f"ツールの実行中にエラーが発生しました: {str(e)}"

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        利用可能なツールのリストを取得

        Returns:
            ツール情報のリスト
        """
        tools_info = []

        for tool_name, tool in self.tools.items():
            schema = tool.get_schema()
            tools_info.append({
                "name": schema.name,
                "description": schema.description,
                "parameters": [param.dict() for param in schema.parameters],
                "category": tool.category,
                "requires_auth": tool.requires_auth,
                "is_dangerous": tool.is_dangerous
            })

        return tools_info

    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        カテゴリ別のツールリストを取得

        Args:
            category: ツールカテゴリ

        Returns:
            該当カテゴリのツール情報リスト
        """
        all_tools = self.get_available_tools()
        return [tool for tool in all_tools if tool.get("category") == category]

    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """
        ツールを検索

        Args:
            query: 検索クエリ

        Returns:
            マッチするツール情報のリスト
        """
        all_tools = self.get_available_tools()
        matching_tools = []

        query_lower = query.lower()

        for tool in all_tools:
            # 名前、説明、パラメータ名で検索
            searchable_text = (
                tool["name"] + " " +
                tool["description"] + " " +
                " ".join([param["name"] for param in tool.get("parameters", [])])
            ).lower()

            if query_lower in searchable_text:
                matching_tools.append(tool)

        return matching_tools

    async def validate_tool_access(self, tool_name: str, user_context: Dict[str, Any]) -> bool:
        """
        ツールアクセスの権限確認

        Args:
            tool_name: ツール名
            user_context: ユーザーコンテキスト

        Returns:
            アクセス可能かどうか
        """
        if tool_name not in self.tools:
            return False

        tool = self.tools[tool_name]

        # 認証が必要なツールのチェック
        if tool.requires_auth:
            # 実際の認証ロジックはここに実装
            # 今回は簡単な実装
            return user_context.get("authenticated", False)

        # 危険なツールのチェック
        if tool.is_dangerous:
            # 管理者権限のチェック
            return user_context.get("admin", False)

        return True

    def get_status(self) -> Dict[str, Any]:
        """ツールレジストリの状態を取得"""
        tool_status = {}
        for tool_name, tool in self.tools.items():
            tool_status[tool_name] = tool.get_status()

        return {
            "initialized": self.is_initialized,
            "total_tools": len(self.tools),
            "tools": tool_status
        }

    async def reload_tool(self, tool_name: str):
        """
        ツールを再読み込み

        Args:
            tool_name: 再読み込みするツール名
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        try:
            logger.info(f"Reloading tool: {tool_name}")

            # 古いツールのクリーンアップ
            old_tool = self.tools[tool_name]
            await old_tool.cleanup()

            # 新しいインスタンスを作成
            tool_class = self.tool_classes[tool_name]
            new_tool = tool_class()

            # 初期化
            await new_tool.initialize()

            # 登録を更新
            self.tools[tool_name] = new_tool

            logger.info(f"Tool {tool_name} reloaded successfully")

        except Exception as e:
            logger.error(f"Failed to reload tool {tool_name}: {e}")
            raise

    async def cleanup(self):
        """リソースのクリーンアップ"""
        logger.info("Cleaning up Tool Registry...")

        # 全ツールのクリーンアップ
        cleanup_tasks = []
        for tool_name, tool in self.tools.items():
            task = tool.cleanup()
            cleanup_tasks.append(task)

        await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        # レジストリをクリア
        self.tools.clear()
        self.tool_classes.clear()
        self.is_initialized = False

        logger.info("Tool Registry cleanup completed")