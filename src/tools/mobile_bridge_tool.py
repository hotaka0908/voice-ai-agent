"""
Mobile Bridge Tool - スマホ連携ブリッジツール

コンパニオンアプリ（スマホ側）と連携し、端末上の操作（アプリ起動、ディープリンク、
メッセージ送信、配車呼び出し、ブラウズ/ナビなど）を安全に依頼するためのツール。

本ツールはあくまで橋渡し層であり、実際の操作はスマホ側アプリがユーザー権限のもとで実行する。
"""

import os
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from src.core.tool_base import Tool, ToolResult, ToolParameter


class MobileBridgeTool(Tool):
    """スマホ側コンパニオンアプリへの操作依頼を行うツール"""

    @property
    def name(self) -> str:
        return "mobile_bridge"

    @property
    def description(self) -> str:
        return (
            "スマホのコンパニオンアプリに操作を依頼します。"
            "アプリ起動/ディープリンク/メッセージ送信/配車/ブラウズ/ナビ等をサポートします。"
        )

    @property
    def category(self) -> str:
        return "mobile"

    @property
    def requires_auth(self) -> bool:
        # スマホ操作は常に認証済みユーザー限定
        return True

    @property
    def is_dangerous(self) -> bool:
        # 端末操作は安全配慮が必要
        return True

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="intent",
                type="string",
                description=(
                    "実行するアクション。例: send_message, open_app, deep_link, "
                    "call_ride, browse, navigate"
                ),
                required=True,
                enum=[
                    "send_message",
                    "open_app",
                    "deep_link",
                    "call_ride",
                    "browse",
                    "navigate",
                ],
            ),
            ToolParameter(
                name="args",
                type="object",
                description="アクション固有のパラメータ（app/to/text/url/destination等）",
                required=False,
                default={},
            ),
            ToolParameter(
                name="confirm",
                type="boolean",
                description="危険操作はユーザー確認を要求（スマホ側でUI確認）",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="timeout",
                type="number",
                description="操作のタイムアウト（秒）",
                required=False,
                default=20,
            ),
        ]

    async def _initialize_impl(self):
        # ブリッジ接続設定
        self.bridge_url: str = os.getenv("MOBILE_BRIDGE_URL", "").rstrip("/")
        self.bridge_token: str = os.getenv("MOBILE_BRIDGE_TOKEN", "")

        # ブリッジ未設定ならモックモード
        self.mock_mode = not bool(self.bridge_url and self.bridge_token)
        if self.mock_mode:
            logger.warning("MobileBridgeTool running in mock mode (no MOBILE_BRIDGE_URL/TOKEN)")

        # 許可アクションと必須引数
        self.intent_specs: Dict[str, Dict[str, Any]] = {
            "send_message": {"required": ["app", "to", "text"]},
            "open_app": {"required": ["app"]},
            "deep_link": {"required": ["url"]},
            "call_ride": {"required": ["service", "pickup", "destination"]},
            "browse": {"required": ["query"]},
            "navigate": {"required": ["destination"]},
        }

        # HTTPクライアント
        self.http_session: Optional["aiohttp.ClientSession"] = None
        if AIOHTTP_AVAILABLE and not self.mock_mode:
            timeout = aiohttp.ClientTimeout(total=15)
            headers = {"Authorization": f"Bearer {self.bridge_token}"}
            self.http_session = aiohttp.ClientSession(timeout=timeout, headers=headers)

    async def _cleanup_impl(self):
        if self.http_session:
            await self.http_session.close()
            self.http_session = None

    def _validate_args(self, intent: str, args: Dict[str, Any]) -> Optional[str]:
        spec = self.intent_specs.get(intent)
        if not spec:
            return f"未対応のintentです: {intent}"
        missing = [k for k in spec.get("required", []) if k not in (args or {})]
        if missing:
            return f"必須パラメータが不足しています: {', '.join(missing)}"
        return None

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            intent = parameters.get("intent")
            args = parameters.get("args", {}) or {}
            confirm = bool(parameters.get("confirm", True))
            timeout = int(parameters.get("timeout", 20))

            # 引数検証
            err = self._validate_args(intent, args)
            if err:
                return ToolResult(success=False, result=None, error=err)

            # 依頼ペイロード
            payload = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "intent": intent,
                "args": args,
                "confirm": confirm,
                "timeout": timeout,
                "agent": "voiceagent",
                "version": "1.0",
            }

            if self.mock_mode:
                # 実機がなくても対話設計を先に進めるためのモック応答
                logger.info(f"[MOCK] Mobile action: {json.dumps(payload, ensure_ascii=False)}")
                return ToolResult(
                    success=True,
                    result={
                        "mode": "mock",
                        "requested": payload,
                        "message": "モバイルブリッジ未設定のためモックで処理しました",
                    },
                )

            if not AIOHTTP_AVAILABLE:
                return ToolResult(
                    success=False,
                    result=None,
                    error="aiohttpがインストールされていません（ブリッジ通信に必要）",
                )

            # 実通信: POST /api/execute へ送信（コンパニオン側の実装に合わせて調整）
            url = f"{self.bridge_url}/api/execute"
            async with self.http_session.post(url, json=payload) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    return ToolResult(
                        success=False,
                        result=None,
                        error=f"ブリッジ応答エラー: {resp.status} {text}",
                    )
                data = await resp.json()
                return ToolResult(success=True, result=data)

        except Exception as e:
            logger.error(f"MobileBridgeTool execution failed: {e}")
            return ToolResult(success=False, result=None, error=str(e))

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            "bridge_configured": not self.mock_mode,
            "bridge_url": bool(self.bridge_url),
        })
        return status

