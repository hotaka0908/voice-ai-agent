"""
Tool Base - ツールの基底クラス

全てのツールが継承する基底クラスとインターフェースを定義
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from loguru import logger


class ToolParameter(BaseModel):
    """ツールのパラメータ定義"""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class ToolSchema(BaseModel):
    """ツールのスキーマ定義"""
    name: str
    description: str
    parameters: List[ToolParameter] = []


class ToolResult(BaseModel):
    """ツールの実行結果"""
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Tool(ABC):
    """
    ツールの基底クラス

    全てのツールはこのクラスを継承し、必要なメソッドを実装する
    """

    def __init__(self):
        self.is_initialized = False
        self.config: Dict[str, Any] = {}

    @property
    @abstractmethod
    def name(self) -> str:
        """ツール名"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """ツールの説明"""
        pass

    @property
    def parameters(self) -> List[ToolParameter]:
        """ツールのパラメータ定義（オーバーライド可能）"""
        return []

    @property
    def category(self) -> str:
        """ツールのカテゴリ（オーバーライド可能）"""
        return "general"

    @property
    def requires_auth(self) -> bool:
        """認証が必要かどうか（オーバーライド可能）"""
        return False

    @property
    def is_dangerous(self) -> bool:
        """危険な操作を含むかどうか（オーバーライド可能）"""
        return False

    def get_schema(self) -> ToolSchema:
        """ツールのスキーマを取得"""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )

    async def initialize(self, config: Optional[Dict[str, Any]] = None):
        """ツールの初期化"""
        try:
            if config:
                self.config.update(config)

            logger.info(f"Initializing tool: {self.name}")
            await self._initialize_impl()

            self.is_initialized = True
            logger.info(f"Tool {self.name} initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize tool {self.name}: {e}")
            raise

    async def _initialize_impl(self):
        """実際の初期化処理（サブクラスでオーバーライド）"""
        pass

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        ツールを実行

        Args:
            parameters: ツールのパラメータ

        Returns:
            実行結果
        """
        pass

    async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """パラメータの検証"""
        try:
            # 必須パラメータのチェック
            required_params = [p.name for p in self.parameters if p.required]
            for param_name in required_params:
                if param_name not in parameters:
                    logger.error(f"Missing required parameter: {param_name}")
                    return False

            # 型チェックとデフォルト値の設定
            for param_def in self.parameters:
                param_name = param_def.name
                if param_name not in parameters:
                    if param_def.default is not None:
                        parameters[param_name] = param_def.default
                    continue

                # 基本的な型チェック
                param_value = parameters[param_name]
                if not self._check_parameter_type(param_value, param_def.type):
                    logger.error(f"Invalid type for parameter {param_name}: expected {param_def.type}")
                    return False

                # enum チェック
                if param_def.enum and param_value not in param_def.enum:
                    logger.error(f"Invalid value for parameter {param_name}: must be one of {param_def.enum}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Parameter validation error: {e}")
            return False

    def _check_parameter_type(self, value: Any, expected_type: str) -> bool:
        """パラメータの型チェック"""
        type_mapping = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }

        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # 不明な型は通す

        return isinstance(value, expected_python_type)

    async def cleanup(self):
        """ツールのクリーンアップ"""
        try:
            logger.info(f"Cleaning up tool: {self.name}")
            await self._cleanup_impl()
            self.is_initialized = False

        except Exception as e:
            logger.error(f"Error cleaning up tool {self.name}: {e}")

    async def _cleanup_impl(self):
        """実際のクリーンアップ処理（サブクラスでオーバーライド）"""
        pass

    def get_status(self) -> Dict[str, Any]:
        """ツールの状態を取得"""
        return {
            "name": self.name,
            "initialized": self.is_initialized,
            "category": self.category,
            "requires_auth": self.requires_auth,
            "is_dangerous": self.is_dangerous
        }

    async def update_config(self, config: Dict[str, Any]):
        """設定を更新"""
        logger.info(f"Updating config for tool {self.name}: {config}")
        self.config.update(config)
        await self._update_config_impl(config)

    async def _update_config_impl(self, config: Dict[str, Any]):
        """実際の設定更新処理（サブクラスでオーバーライド）"""
        pass


class AsyncTool(Tool):
    """
    非同期ツールの基底クラス

    長時間実行されるツールや外部APIを呼び出すツールに使用
    """

    @abstractmethod
    async def execute_async(self, parameters: Dict[str, Any]) -> ToolResult:
        """非同期でツールを実行"""
        pass

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """execute メソッドを非同期版にリダイレクト"""
        return await self.execute_async(parameters)


class StreamingTool(Tool):
    """
    ストリーミングツールの基底クラス

    結果を段階的に返すツールに使用
    """

    @abstractmethod
    async def execute_stream(self, parameters: Dict[str, Any]):
        """ストリーミングでツールを実行（ジェネレーター）"""
        pass

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """ストリーミング結果を最終結果にまとめる"""
        results = []
        async for chunk in self.execute_stream(parameters):
            results.append(chunk)

        return ToolResult(
            success=True,
            result=results,
            metadata={"stream": True, "chunks": len(results)}
        )