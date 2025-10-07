"""
Tool Registry - ツール管理システム

各種ツールの登録、管理、実行を行うシステム
"""

import asyncio
from typing import Dict, Any, List, Optional, Type
from loguru import logger

from src.core.tool_base import Tool, ToolResult
import importlib


class ToolRegistry:
    """
    ツールの登録・管理・実行を行うクラス

    各種ツールを動的に登録し、実行時に適切なツールを選択して実行する
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.tool_classes: Dict[str, Type[Tool]] = {}
        self.is_initialized = False
        # 組み込みツールの名前→実装マップ
        self._builtin_map: Dict[str, str] = {
            "weather": "src.tools.weather_tool:WeatherTool",
            "time": "src.tools.time_tool:TimeTool",
            "calculator": "src.tools.calculator_tool:CalculatorTool",
            "memory": "src.tools.memory_tool:MemoryTool",
            "search": "src.tools.search_tool:SearchTool",
            "mobile_bridge": "src.tools.mobile_bridge_tool:MobileBridgeTool",
            "mcp": "src.tools.mcp_tool:MCPTool",
            "gmail": "src.tools.gmail_tool:GmailTool",
            "calendar": "src.tools.calendar_tool:CalendarTool",
            "calendar_mcp": "src.tools.calendar_mcp_tool:CalendarMCPTool",
            "alarm": "src.tools.alarm_tool:AlarmTool",
            "vision": "src.tools.vision_tool:VisionTool",
            "aircon": "src.tools.dummy_tools:AirconTool",
            "light": "src.tools.dummy_tools:LightTool",
            "taxi": "src.tools.dummy_tools:TaxiTool",
            "robot": "src.tools.dummy_tools:RobotTool",
        }

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
        """組み込みツールの登録（個別に失敗を許容）"""
        tool_classes = []

        # 個別インポートで、失敗しても他ツールの登録を継続
        def _try_import(importer, name):
            try:
                cls = importer()
                tool_classes.append(cls)
            except ImportError as e:
                logger.warning(f"Built-in tool '{name}' not available: {e}")
            except Exception as e:
                logger.error(f"Failed to load tool '{name}': {e}")

        _try_import(lambda: __import__('src.tools.time_tool', fromlist=['TimeTool']).TimeTool, 'time')
        _try_import(lambda: __import__('src.tools.calculator_tool', fromlist=['CalculatorTool']).CalculatorTool, 'calculator')
        _try_import(lambda: __import__('src.tools.memory_tool', fromlist=['MemoryTool']).MemoryTool, 'memory')
        _try_import(lambda: __import__('src.tools.weather_tool', fromlist=['WeatherTool']).WeatherTool, 'weather')
        _try_import(lambda: __import__('src.tools.search_tool', fromlist=['SearchTool']).SearchTool, 'search')
        _try_import(lambda: __import__('src.tools.mobile_bridge_tool', fromlist=['MobileBridgeTool']).MobileBridgeTool, 'mobile_bridge')
        _try_import(lambda: __import__('src.tools.mcp_tool', fromlist=['MCPTool']).MCPTool, 'mcp')
        _try_import(lambda: __import__('src.tools.gmail_tool', fromlist=['GmailTool']).GmailTool, 'gmail')
        # _try_import(lambda: __import__('src.tools.calendar_tool', fromlist=['CalendarTool']).CalendarTool, 'calendar')  # Disabled: use calendar_mcp instead
        _try_import(lambda: __import__('src.tools.calendar_mcp_tool', fromlist=['CalendarMCPTool']).CalendarMCPTool, 'calendar_mcp')
        _try_import(lambda: __import__('src.tools.alarm_tool', fromlist=['AlarmTool']).AlarmTool, 'alarm')
        _try_import(lambda: __import__('src.tools.vision_tool', fromlist=['VisionTool']).VisionTool, 'vision')
        _try_import(lambda: __import__('src.tools.dummy_tools', fromlist=['AirconTool']).AirconTool, 'aircon')
        _try_import(lambda: __import__('src.tools.dummy_tools', fromlist=['LightTool']).LightTool, 'light')
        _try_import(lambda: __import__('src.tools.dummy_tools', fromlist=['TaxiTool']).TaxiTool, 'taxi')
        _try_import(lambda: __import__('src.tools.dummy_tools', fromlist=['RobotTool']).RobotTool, 'robot')

        # インスタンス化して登録
        for tool_cls in tool_classes:
            try:
                await self.register_tool(tool_cls())
            except Exception as e:
                logger.error(f"Failed to register tool instance '{tool_cls}': {e}")

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
            # 動的ロードを試行
            try:
                await self.ensure_tool(tool_name)
            except Exception as e:
                logger.error(f"Failed to ensure tool {tool_name}: {e}")
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
                    # ToolResultオブジェクト全体を返す（メタデータを保持）
                    return result
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
            # Pydantic v2 互換: .dict() ではなく .model_dump() を使用
            # Pydantic v2: model_dump(), v1: dict()
            def _to_dict(p):
                if hasattr(p, "model_dump"):
                    return p.model_dump()
                if hasattr(p, "dict"):
                    return p.dict()
                try:
                    return dict(p)
                except Exception:
                    return {
                        "name": getattr(p, "name", None),
                        "type": getattr(p, "type", None),
                        "description": getattr(p, "description", None),
                        "required": getattr(p, "required", False),
                        "default": getattr(p, "default", None),
                        "enum": getattr(p, "enum", None),
                    }

            params = [_to_dict(param) for param in schema.parameters]
            tools_info.append({
                "name": schema.name,
                "description": schema.description,
                "parameters": params,
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

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        ツールインスタンスを取得

        Args:
            tool_name: ツール名

        Returns:
            ツールインスタンス、見つからない場合はNone
        """
        return self.tools.get(tool_name)

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

    async def get_status(self) -> Dict[str, Any]:
        """ツールレジストリの状態を取得"""
        import asyncio as _asyncio
        tool_status = {}
        for tool_name, tool in self.tools.items():
            status = tool.get_status()
            # ツール側のget_statusが非同期の場合はawait
            if _asyncio.iscoroutine(status):
                status = await status
            tool_status[tool_name] = status

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

    async def ensure_tool(self, tool_name: str):
        """ツールが未登録なら組み込みからロードして登録する"""
        if tool_name in self.tools:
            return

        if tool_name not in self._builtin_map:
            raise ValueError(f"Unknown tool: {tool_name}")

        module_path, cls_name = self._builtin_map[tool_name].split(":")
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, cls_name)
            instance: Tool = cls()
            await self.register_tool(instance)
            await instance.initialize()
            logger.info(f"Dynamically loaded and initialized tool: {tool_name}")
        except ImportError as e:
            logger.warning(f"Tool {tool_name} import failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Tool {tool_name} dynamic load failed: {e}")
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
