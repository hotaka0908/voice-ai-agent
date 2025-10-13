"""
Context Manager - 会話コンテキスト管理

会話の流れ、ユーザーの意図、セッション情報を管理する
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import json


class Message:
    """会話メッセージを表すクラス"""

    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None):
        self.role = role  # "user", "assistant", "system"
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class ContextManager:
    """会話コンテキストを管理するクラス"""

    def __init__(self, max_messages: int = 50, context_window_hours: int = 2):
        self.messages: List[Message] = []
        self.max_messages = max_messages
        self.context_window = timedelta(hours=context_window_hours)
        self.session_start = datetime.now()
        self.user_preferences: Dict[str, Any] = {}
        self.current_topic: Optional[str] = None
        self.latest_email_id: Optional[str] = None  # 最新のメールIDを保存
        self.is_initialized = False

        # メール状態トラッキング
        self.email_state = {
            "last_action": None,  # "list", "read", "reply"
            "shown_email_ids": [],  # 既に表示したメールID
            "last_shown_count": 0,  # 前回表示した件数
            "total_available": None,  # 利用可能な総メール数
            "current_offset": 0,  # 現在のオフセット（次に表示する位置）
        }

    async def initialize(self):
        """コンテキストマネージャーの初期化"""
        try:
            logger.info("Initializing Context Manager...")

            # システムメッセージの追加
            system_message = Message(
                role="system",
                content="あなたは親切で知的な音声AIアシスタントです。"
                       "ユーザーの指示を理解し、適切なツールを使用して最適な支援を提供してください。"
                       "自然で親しみやすい口調で会話してください。"
            )
            self.messages.append(system_message)

            self.is_initialized = True
            logger.info("Context Manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Context Manager: {e}")
            raise

    async def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """ユーザーメッセージを追加"""
        message = Message("user", content)
        if metadata:
            message.metadata.update(metadata)

        self.messages.append(message)
        await self._update_topic(content)
        await self._cleanup_old_messages()

        logger.debug(f"Added user message: {content[:50]}...")

    async def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """アシスタントメッセージを追加"""
        message = Message("assistant", content)
        if metadata:
            message.metadata.update(metadata)

        self.messages.append(message)
        await self._cleanup_old_messages()

        logger.debug(f"Added assistant message: {content[:50]}...")

    async def add_system_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """システムメッセージを追加"""
        message = Message("system", content)
        if metadata:
            message.metadata.update(metadata)

        self.messages.append(message)
        logger.debug(f"Added system message: {content[:50]}...")

    def get_context(self, include_system: bool = True) -> List[Dict[str, Any]]:
        """現在のコンテキストを取得"""
        messages = self.messages.copy()

        if not include_system:
            messages = [msg for msg in messages if msg.role != "system"]

        return [msg.to_dict() for msg in messages]

    def get_recent_context(self, message_count: int = 10) -> List[Dict[str, Any]]:
        """最近のメッセージを取得"""
        recent_messages = self.messages[-message_count:]
        return [msg.to_dict() for msg in recent_messages]

    def get_conversation_summary(self) -> str:
        """会話の要約を生成"""
        if len(self.messages) <= 1:  # システムメッセージのみ
            return "会話が開始されたばかりです。"

        user_messages = [msg for msg in self.messages if msg.role == "user"]
        assistant_messages = [msg for msg in self.messages if msg.role == "assistant"]

        summary = f"会話開始: {self.session_start.strftime('%Y-%m-%d %H:%M')}\n"
        summary += f"メッセージ数: ユーザー {len(user_messages)}, アシスタント {len(assistant_messages)}\n"

        if self.current_topic:
            summary += f"現在のトピック: {self.current_topic}\n"

        # 最近の会話を要約
        recent_messages = self.messages[-6:]  # 最新6メッセージ
        if recent_messages:
            summary += "\n最近の会話:\n"
            for msg in recent_messages:
                if msg.role != "system":
                    content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    summary += f"- {msg.role}: {content_preview}\n"

        return summary

    async def update_user_preferences(self, preferences: Dict[str, Any]):
        """ユーザー設定を更新"""
        self.user_preferences.update(preferences)
        logger.info(f"Updated user preferences: {preferences}")

    def get_user_preferences(self) -> Dict[str, Any]:
        """ユーザー設定を取得"""
        return self.user_preferences.copy()

    async def _update_topic(self, user_message: str):
        """現在のトピックを更新（簡単な実装）"""
        # より高度なトピック検出は後で実装
        keywords = {
            "天気": ["天気", "気温", "雨", "晴れ", "曇り"],
            "音楽": ["音楽", "曲", "歌", "再生", "プレイリスト"],
            "照明": ["電気", "照明", "ライト", "明かり"],
            "予定": ["予定", "スケジュール", "カレンダー", "会議"],
            "メモ": ["メモ", "記録", "覚えて", "保存"]
        }

        for topic, topic_keywords in keywords.items():
            if any(keyword in user_message for keyword in topic_keywords):
                if self.current_topic != topic:
                    logger.info(f"Topic changed to: {topic}")
                    self.current_topic = topic
                break

    async def _cleanup_old_messages(self):
        """古いメッセージをクリーンアップ"""
        # メッセージ数制限
        if len(self.messages) > self.max_messages:
            # システムメッセージは保持
            system_messages = [msg for msg in self.messages if msg.role == "system"]
            other_messages = [msg for msg in self.messages if msg.role != "system"]

            # 古いメッセージを削除
            keep_count = self.max_messages - len(system_messages)
            if keep_count > 0:
                other_messages = other_messages[-keep_count:]

            self.messages = system_messages + other_messages
            logger.debug(f"Cleaned up messages. Current count: {len(self.messages)}")

        # 時間制限（古いメッセージを削除）
        cutoff_time = datetime.now() - self.context_window
        original_count = len(self.messages)

        # システムメッセージは時間制限の対象外
        self.messages = [
            msg for msg in self.messages
            if msg.role == "system" or msg.timestamp > cutoff_time
        ]

        if len(self.messages) < original_count:
            logger.debug(f"Removed {original_count - len(self.messages)} old messages")

    def get_status(self) -> Dict[str, Any]:
        """コンテキストマネージャーの状態を取得"""
        return {
            "initialized": self.is_initialized,
            "message_count": len(self.messages),
            "current_topic": self.current_topic,
            "session_duration": str(datetime.now() - self.session_start),
            "user_preferences_count": len(self.user_preferences)
        }

    async def reset_context(self):
        """コンテキストをリセット"""
        logger.info("Resetting conversation context...")

        # システムメッセージのみ保持
        system_messages = [msg for msg in self.messages if msg.role == "system"]
        self.messages = system_messages

        self.current_topic = None
        self.session_start = datetime.now()
        logger.info("Context reset completed")

    def set_latest_email_id(self, email_id: str):
        """最新のメールIDを設定"""
        self.latest_email_id = email_id
        logger.debug(f"Latest email ID set: {email_id}")

    def get_latest_email_id(self) -> Optional[str]:
        """最新のメールIDを取得"""
        return self.latest_email_id

    def clear_latest_email_id(self):
        """最新のメールIDをクリア"""
        self.latest_email_id = None
        logger.debug("Latest email ID cleared")

    # メール状態管理メソッド
    def update_email_state(self, action: str, shown_ids: List[str], shown_count: int):
        """メール表示状態を更新"""
        self.email_state["last_action"] = action
        self.email_state["shown_email_ids"].extend(shown_ids)
        self.email_state["last_shown_count"] = shown_count
        self.email_state["current_offset"] += shown_count
        logger.debug(f"Updated email state: action={action}, shown={shown_count}, offset={self.email_state['current_offset']}")

    def get_email_state(self) -> Dict[str, Any]:
        """現在のメール状態を取得"""
        return self.email_state.copy()

    def reset_email_state(self):
        """メール状態をリセット"""
        self.email_state = {
            "last_action": None,
            "shown_email_ids": [],
            "last_shown_count": 0,
            "total_available": None,
            "current_offset": 0,
        }
        logger.debug("Email state reset")

    def has_shown_emails(self) -> bool:
        """既にメールを表示したかどうか"""
        return len(self.email_state["shown_email_ids"]) > 0

    async def cleanup(self):
        """クリーンアップ処理"""
        logger.info("Cleaning up Context Manager...")
        # 必要に応じてコンテキストを保存
        self.messages.clear()
        self.user_preferences.clear()
        self.latest_email_id = None
        self.reset_email_state()
        self.is_initialized = False