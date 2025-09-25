"""
MCP Tool - Model Context Protocol クライアントツール（スタブ）

目的:
  - 単一の抽象化ツールで、複数のMCPサーバ（Gmail/Calendar/Drive/Browser等）に接続し、
    ツール呼び出しやリソース取得を行うための土台を提供する。

現状:
  - 簡易スタブ（モック）として実装。実通信は後続で 'mcp' ライブラリ等に置換する。
"""

import os
import json
from typing import Dict, Any, List, Optional
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter


class MCPTool(Tool):
    """MCPサーバ経由のツール呼び出し/リソース取得を抽象化するツール"""

    @property
    def name(self) -> str:
        return "mcp"

    @property
    def description(self) -> str:
        return (
            "Model Context Protocol 経由で外部サービス（Gmail/Calendar等）のツールや"
            "リソースにアクセスします（スタブ）。"
        )

    @property
    def category(self) -> str:
        return "mcp"

    @property
    def requires_auth(self) -> bool:
        return True

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="server",
                type="string",
                description="接続先MCPサーバ名（例: gmail, calendar, drive, browser）",
                required=True,
            ),
            ToolParameter(
                name="action",
                type="string",
                description="呼び出す操作種別: tool（ツール呼び出し）/ resource（リソース取得）",
                required=True,
                enum=["tool", "resource"],
            ),
            ToolParameter(
                name="name",
                type="string",
                description="ツール名 or リソース名",
                required=True,
            ),
            ToolParameter(
                name="arguments",
                type="object",
                description="ツール呼び出しの引数（resource時はクエリ等）",
                required=False,
                default={},
            ),
        ]

    async def _initialize_impl(self):
        # MCPサーバ設定を読み込み
        # 形式例: MCP_SERVERS='{"gmail":{"endpoint":"http://localhost:9001","token":"..."}}'
        self.servers: Dict[str, Dict[str, Any]] = {}
        raw = os.getenv("MCP_SERVERS", "").strip()
        if raw:
            try:
                self.servers = json.loads(raw)
            except Exception as e:
                logger.error(f"Failed to parse MCP_SERVERS: {e}")
        if not self.servers:
            logger.warning("MCPTool running with empty server registry (mock mode)")

        # 送信方式（現状はHTTP JSON-RPC想定。serverごとに上書き可能）
        self.default_transport = "http_jsonrpc"
        for name, cfg in self.servers.items():
            cfg.setdefault("transport", self.default_transport)
        # 実通信クライアントは後続で拡充（stdio/WebSocket等）。

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            server = str(parameters.get("server", "")).lower()
            action = parameters.get("action")
            name = parameters.get("name")
            args = parameters.get("arguments", {}) or {}

            if not server or not action or not name:
                return ToolResult(success=False, result=None, error="必須パラメータ不足")

            server_cfg = self.servers.get(server)
            if not server_cfg:
                # 未設定サーバはモック応答
                logger.info(f"[MCP MOCK] server={server} action={action} name={name} args={args}")
                return ToolResult(
                    success=True,
                    result={
                        "mode": "mock",
                        "server": server,
                        "action": action,
                        "name": name,
                        "arguments": args,
                        "message": "MCPサーバ未設定のためモック応答",
                    },
                )

            # 実通信: HTTP JSON-RPC を優先実装
            transport = server_cfg.get("transport", self.default_transport)
            endpoint = server_cfg.get("endpoint")
            token = server_cfg.get("token")

            if not endpoint:
                return ToolResult(success=False, result=None, error="MCPサーバendpoint未設定")

            if transport == "http_jsonrpc":
                method, params = self._build_jsonrpc_call(action, name, args)
                resp = await self._http_jsonrpc_call(endpoint, token, method, params)
                return resp

            # 未対応transportはスタブにフォールバック
            logger.info(f"[MCP STUB transport] {transport} {server} {action}:{name} {args}")
            return ToolResult(
                success=True,
                result={
                    "mode": "stub",
                    "server": server,
                    "endpoint": endpoint,
                    "transport": transport,
                    "action": action,
                    "name": name,
                    "arguments": args,
                    "note": "未対応transportのためスタブ応答",
                },
            )

        except Exception as e:
            logger.error(f"MCPTool execution failed: {e}")
            return ToolResult(success=False, result=None, error=str(e))

    def _build_jsonrpc_call(self, action: str, name: str, args: Dict[str, Any]):
        """MCPの典型的なJSON-RPCメソッド/パラメータに変換"""
        if action == "tool":
            method = "tools/call"
            params = {"name": name, "arguments": args}
        elif action == "resource":
            method = "resources/read"
            # nameをリソース識別子に、そのほかはオプション
            params = {"uri": name, "options": args}
        else:
            # 拡張用: tools/list 等
            method = action
            params = {"name": name, **({"arguments": args} if args else {})}
        return method, params

    async def _http_jsonrpc_call(self, endpoint: str, token: Optional[str], method: str, params: Dict[str, Any]) -> ToolResult:
        if not AIOHTTP_AVAILABLE:
            return ToolResult(success=False, result=None, error="aiohttp未インストール")

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with self.http_session.post(endpoint, json=payload, headers=headers) as resp:
            text = await resp.text()
            if resp.status != 200:
                return ToolResult(success=False, result=None, error=f"HTTP {resp.status}: {text}")

            try:
                data = json.loads(text)
            except Exception:
                return ToolResult(success=False, result=None, error=f"Invalid JSON: {text}")

            if "error" in data:
                return ToolResult(success=False, result=None, error=str(data["error"]))

            return ToolResult(success=True, result=data.get("result"))
