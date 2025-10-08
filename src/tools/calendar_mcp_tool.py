"""
Calendar MCP Tool - Google Calendar統合（MCP経由）

deciduus/calendar-mcpサーバーとMCPプロトコルで通信し、
音声コマンドでカレンダー操作を実現
"""

import asyncio
import json
import subprocess
from typing import Optional, Dict, Any
from loguru import logger
from src.core.tool_base import Tool, ToolResult


class CalendarMCPTool(Tool):
    """Google Calendar MCP統合ツール"""

    name = "calendar"
    description = "Googleカレンダーの操作（予定確認・作成・更新・削除）"

    def __init__(self):
        super().__init__()
        self.server_process: Optional[subprocess.Popen] = None
        self.server_ready = False

    async def initialize(self):
        """MCPサーバーの初期化（直接Google Calendar APIを使用）"""
        try:
            logger.info("Initializing Calendar MCP tool...")

            # MCPサーバーは使用せず、直接Google Calendar APIを呼び出す
            # OAuth認証情報の読み込み
            import sys
            import os

            calendar_mcp_path = os.path.abspath("./mcp_servers/calendar-mcp")
            if calendar_mcp_path not in sys.path:
                sys.path.insert(0, calendar_mcp_path)

            from dotenv import load_dotenv
            env_path = os.path.join(calendar_mcp_path, ".env")
            load_dotenv(env_path)

            # モジュール名の衝突を避けるため直接インポート
            import importlib.util
            spec = importlib.util.spec_from_file_location("calendar_auth", os.path.join(calendar_mcp_path, "src", "auth.py"))
            auth_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(auth_module)

            from googleapiclient.discovery import build

            self.creds = auth_module.get_credentials()
            self.service = build('calendar', 'v3', credentials=self.creds)
            self.server_ready = True

            logger.info("✅ Calendar tool initialized successfully")
            return

            # サーバー起動確認（初回のレスポンスを待つ）
            await asyncio.sleep(2)

            if self.server_process.poll() is None:
                self.server_ready = True
                logger.info("✅ Calendar MCP server started successfully")
            else:
                stderr_output = self.server_process.stderr.read()
                logger.error(f"❌ Calendar MCP server failed to start: {stderr_output}")
                self.server_ready = False

        except Exception as e:
            logger.error(f"Failed to initialize Calendar MCP: {e}")
            self.server_ready = False

    async def cleanup(self):
        """MCPサーバーの停止"""
        if self.server_process:
            try:
                logger.info("Stopping Calendar MCP server...")
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                logger.info("✅ Calendar MCP server stopped")
            except Exception as e:
                logger.error(f"Error stopping MCP server: {e}")
                self.server_process.kill()
            finally:
                self.server_process = None
                self.server_ready = False

    async def _send_mcp_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCPリクエスト送信"""
        if not self.server_ready or not self.server_process:
            raise RuntimeError("Calendar MCP server not ready")

        try:
            # MCP JSON-RPC リクエスト構築
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }

            # リクエスト送信
            request_json = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_json)
            self.server_process.stdin.flush()

            # レスポンス受信
            response_line = self.server_process.stdout.readline()
            response = json.loads(response_line)

            if "error" in response:
                raise RuntimeError(f"MCP Error: {response['error']}")

            return response.get("result", {})

        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            raise

    async def execute(self, params: dict) -> ToolResult:
        """
        カレンダー操作実行

        Args:
            params: {
                "action": "list_events" | "list" | "create_event" | "update_event" | "delete_event",
                "calendar_id": str (optional),
                "time_min": str (optional, ISO8601),
                "time_max": str (optional, ISO8601),
                "max_results": int (optional),
                "event_id": str (optional, for update/delete),
                "event": dict (optional, for create/update)
            }
        """
        try:
            action = params.get("action", "list_events")

            # "list" を "list_events" にマッピング
            if action == "list":
                action = "list_events"

            logger.info(f"Executing calendar action: {action}")

            # アクション別処理
            if action == "list_events":
                result = await self._list_events(params)
            elif action == "create_event":
                result = await self._create_event(params)
            elif action == "update_event":
                result = await self._update_event(params)
            elif action == "delete_event":
                result = await self._delete_event(params)
            elif action == "find_free_slots":
                result = await self._find_free_slots(params)
            else:
                return ToolResult(
                    success=False,
                    result={"error": f"Unknown action: {action}"}
                )

            return ToolResult(success=True, result=result)

        except Exception as e:
            logger.error(f"Calendar MCP tool execution failed: {e}")
            return ToolResult(
                success=False,
                result={"error": str(e)}
            )

    async def _list_events(self, params: dict) -> Dict[str, Any]:
        """予定一覧取得"""
        from datetime import datetime, timedelta
        import asyncio

        calendar_id = params.get("calendar_id", "primary")

        # デフォルト: 今日から1週間
        if not params.get("time_min"):
            time_min = datetime.utcnow().isoformat() + 'Z'
        else:
            time_min = params.get("time_min")

        if not params.get("time_max"):
            time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
        else:
            time_max = params.get("time_max")

        max_results = params.get("max_results", 10)

        # Google Calendar API呼び出し（非同期化）
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
        )

        # イベントを整形
        events = response.get("events", [])
        formatted_events = []

        for event in events:
            formatted_events.append({
                "id": event.get("id"),
                "summary": event.get("summary", "(タイトルなし)"),
                "start": event.get("start", {}).get("dateTime") or event.get("start", {}).get("date"),
                "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"),
                "location": event.get("location"),
                "description": event.get("description")
            })

        return {
            "events": formatted_events,
            "count": len(formatted_events)
        }

    async def _create_event(self, params: dict) -> Dict[str, Any]:
        """予定作成"""
        event_data = params.get("event", {})

        mcp_params = {
            "calendar_id": params.get("calendar_id", "primary"),
            "summary": event_data.get("summary"),
            "start_time": event_data.get("start"),
            "end_time": event_data.get("end"),
            "description": event_data.get("description"),
            "location": event_data.get("location"),
            "attendees": event_data.get("attendees", [])
        }

        # None値を削除
        mcp_params = {k: v for k, v in mcp_params.items() if v is not None}

        response = await self._send_mcp_request(
            "mcp_google_calendar_create_event",
            mcp_params
        )

        return {
            "event_id": response.get("event_id"),
            "summary": response.get("summary"),
            "status": "created"
        }

    async def _update_event(self, params: dict) -> Dict[str, Any]:
        """予定更新"""
        event_data = params.get("event", {})

        mcp_params = {
            "calendar_id": params.get("calendar_id", "primary"),
            "event_id": params.get("event_id"),
            "summary": event_data.get("summary"),
            "start_time": event_data.get("start"),
            "end_time": event_data.get("end"),
            "description": event_data.get("description"),
            "location": event_data.get("location")
        }

        # None値を削除
        mcp_params = {k: v for k, v in mcp_params.items() if v is not None}

        response = await self._send_mcp_request(
            "mcp_google_calendar_update_event",
            mcp_params
        )

        return {
            "event_id": response.get("event_id"),
            "status": "updated"
        }

    async def _delete_event(self, params: dict) -> Dict[str, Any]:
        """予定削除"""
        mcp_params = {
            "calendar_id": params.get("calendar_id", "primary"),
            "event_id": params.get("event_id")
        }

        response = await self._send_mcp_request(
            "mcp_google_calendar_delete_event",
            mcp_params
        )

        return {
            "event_id": params.get("event_id"),
            "status": "deleted"
        }

    async def _find_free_slots(self, params: dict) -> Dict[str, Any]:
        """空き時間検索"""
        mcp_params = {
            "calendars": params.get("calendars", ["primary"]),
            "time_min": params.get("time_min"),
            "time_max": params.get("time_max")
        }

        response = await self._send_mcp_request(
            "mcp_google_calendar_query_free_busy",
            mcp_params
        )

        return response
