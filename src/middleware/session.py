"""
Session Management Middleware

マルチユーザー対応のためのセッション管理
各ユーザーを一意のセッションIDで識別し、データを分離する
"""

import os
import re
from typing import Optional
from pathlib import Path
from loguru import logger


class SessionManager:
    """セッション管理クラス"""

    def __init__(self):
        self.sessions_dir = "data/sessions"
        self._ensure_sessions_dir()

    def _ensure_sessions_dir(self):
        """セッションディレクトリを作成"""
        os.makedirs(self.sessions_dir, exist_ok=True)
        logger.info(f"Sessions directory initialized: {self.sessions_dir}")

    def validate_session_id(self, session_id: str) -> bool:
        """
        セッションIDの形式を検証

        Args:
            session_id: 検証するセッションID

        Returns:
            bool: 有効な場合True

        セキュリティ:
            - UUID v4形式のみ許可
            - パストラバーサル攻撃を防ぐ
        """
        if not session_id:
            return False

        # UUID v4形式の検証（8-4-4-4-12の形式）
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )

        if not uuid_pattern.match(session_id):
            logger.warning(f"Invalid session ID format: {session_id}")
            return False

        # パストラバーサル攻撃のチェック
        if '..' in session_id or '/' in session_id or '\\' in session_id:
            logger.error(f"Path traversal attempt detected: {session_id}")
            return False

        return True

    def get_session_dir(self, session_id: str) -> Path:
        """
        セッションディレクトリのパスを取得

        Args:
            session_id: セッションID

        Returns:
            Path: セッションディレクトリのパス
        """
        if not self.validate_session_id(session_id):
            raise ValueError(f"Invalid session ID: {session_id}")

        session_dir = Path(self.sessions_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        return session_dir

    def get_data_path(self, session_id: str, data_type: str) -> Path:
        """
        ユーザーデータのパスを取得

        Args:
            session_id: セッションID
            data_type: データタイプ（例: "gmail_token", "personal_memory"）

        Returns:
            Path: データファイルのパス
        """
        session_dir = self.get_session_dir(session_id)
        return session_dir / f"{data_type}.json"

    def get_gmail_token_path(self, session_id: str) -> str:
        """
        Gmailトークンのパスを取得

        Args:
            session_id: セッションID

        Returns:
            str: Gmailトークンファイルのパス
        """
        return str(self.get_data_path(session_id, "gmail_token"))

    def get_gmail_credentials_path(self, session_id: str) -> str:
        """
        Gmail認証情報のパスを取得（全ユーザー共通）

        Returns:
            str: Gmail認証情報ファイルのパス
        """
        # 認証情報は全ユーザー共通
        return "data/gmail_credentials.json"

    def session_exists(self, session_id: str) -> bool:
        """
        セッションが存在するか確認

        Args:
            session_id: セッションID

        Returns:
            bool: セッションが存在する場合True
        """
        if not self.validate_session_id(session_id):
            return False

        session_dir = Path(self.sessions_dir) / session_id
        return session_dir.exists()

    def list_sessions(self) -> list:
        """
        全セッションのリストを取得（デバッグ用）

        Returns:
            list: セッションIDのリスト
        """
        sessions_path = Path(self.sessions_dir)
        if not sessions_path.exists():
            return []

        return [d.name for d in sessions_path.iterdir() if d.is_dir()]


# グローバルインスタンス
session_manager = SessionManager()
