"""
Vision Tool - カメラ画像認識ツール

OpenAI Vision APIを使用して画像を分析し、視覚的な情報を提供する
"""

import os
import base64
from typing import Dict, Any, Optional, List
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter


class VisionTool(Tool):
    """カメラ画像認識ツール"""

    def __init__(self):
        super().__init__()
        self.client = None
        self.model = "gpt-4o"  # OpenAI Vision対応モデル

    @property
    def name(self) -> str:
        return "vision"

    @property
    def description(self) -> str:
        return "カメラで撮影した画像を分析して、現実世界の情報を認識します"

    @property
    def category(self) -> str:
        return "information"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="image",
                type="string",
                description="Base64エンコードされた画像データ（data:image/jpeg;base64,... の形式）",
                required=True
            ),
            ToolParameter(
                name="query",
                type="string",
                description="画像に対する質問や分析リクエスト（例: 「これは何ですか？」「周囲の状況を教えて」）",
                required=False,
                default="この画像について詳しく教えてください"
            )
        ]

    async def _initialize_impl(self):
        """ツールの初期化"""
        try:
            from openai import AsyncOpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")

            self.client = AsyncOpenAI(api_key=api_key)
            logger.info("Vision tool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Vision tool: {e}")
            raise

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        画像を分析して結果を返す

        Args:
            params: {
                "image": "data:image/jpeg;base64,...",
                "query": "画像に対する質問"
            }

        Returns:
            ToolResult with analysis result
        """
        try:
            image_data = params.get("image")
            query = params.get("query", "この画像について詳しく教えてください")

            if not image_data:
                return ToolResult(
                    success=False,
                    result="画像データが提供されていません",
                    metadata={"error": "missing_image"}
                )

            logger.info(f"Analyzing image with query: {query}")

            # OpenAI Vision APIで画像分析
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": query
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )

            # 分析結果を取得
            analysis_result = response.choices[0].message.content

            logger.info(f"Vision analysis completed: {analysis_result[:100]}...")

            return ToolResult(
                success=True,
                result=f"🔍 画像分析結果:\n\n{analysis_result}",
                metadata={
                    "model": self.model,
                    "query": query,
                    "tokens_used": response.usage.total_tokens
                }
            )

        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return ToolResult(
                success=False,
                result=f"画像分析中にエラーが発生しました: {str(e)}",
                metadata={"error": str(e)}
            )

    async def _cleanup_impl(self):
        """リソースのクリーンアップ"""
        if self.client:
            await self.client.close()
        logger.info("Vision tool cleaned up")
