"""
WebSocket Manager - WebSocket接続管理

複数のWebSocket接続を管理し、メッセージのブロードキャストを行う
"""

from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
import json


class WebSocketManager:
    """WebSocket接続を管理するクラス"""

    def __init__(self):
        # アクティブなWebSocket接続のリスト
        self.active_connections: List[WebSocket] = []
        # 接続別の情報を保存
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket):
        """新しいWebSocket接続を受け入れる"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "connected_at": None,  # タイムスタンプは実装時に追加
            "user_id": None,
            "session_id": None
        }
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """WebSocket接続を切断する"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            if websocket in self.connection_info:
                del self.connection_info[websocket]
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """特定のWebSocketに個人メッセージを送信"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)

    async def send_personal_json(self, data: Dict[str, Any], websocket: WebSocket):
        """特定のWebSocketにJSONデータを送信"""
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Failed to send personal JSON: {e}")
            self.disconnect(websocket)

    async def send_personal_bytes(self, data: bytes, websocket: WebSocket):
        """特定のWebSocketにバイナリデータを送信"""
        try:
            await websocket.send_bytes(data)
        except Exception as e:
            logger.error(f"Failed to send personal bytes: {e}")
            self.disconnect(websocket)

    async def broadcast_message(self, message: str):
        """全てのアクティブなWebSocketにメッセージをブロードキャスト"""
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")
                disconnected.append(connection)

        # 切断された接続を削除
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_json(self, data: Dict[str, Any]):
        """全てのアクティブなWebSocketにJSONデータをブロードキャスト"""
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Failed to broadcast JSON: {e}")
                disconnected.append(connection)

        # 切断された接続を削除
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_bytes(self, data: bytes):
        """全てのアクティブなWebSocketにバイナリデータをブロードキャスト"""
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_bytes(data)
            except Exception as e:
                logger.error(f"Failed to broadcast bytes: {e}")
                disconnected.append(connection)

        # 切断された接続を削除
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_count(self) -> int:
        """アクティブな接続数を取得"""
        return len(self.active_connections)

    def get_connection_info(self, websocket: WebSocket) -> Dict[str, Any]:
        """特定の接続の情報を取得"""
        return self.connection_info.get(websocket, {})

    def update_connection_info(self, websocket: WebSocket, info: Dict[str, Any]):
        """接続情報を更新"""
        if websocket in self.connection_info:
            self.connection_info[websocket].update(info)

    def get_all_connections_info(self) -> Dict[str, Any]:
        """全ての接続の情報を取得"""
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "connection_id": id(ws),
                    **info
                }
                for ws, info in self.connection_info.items()
            ]
        }