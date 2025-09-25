"""
Time Tool - 時刻・日付取得ツール

現在時刻、日付、タイムゾーン情報などを提供するツール
"""

from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, List
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter


class TimeTool(Tool):
    """時刻・日付情報を取得するツール"""

    @property
    def name(self) -> str:
        return "time"

    @property
    def description(self) -> str:
        return "現在の時刻、日付、タイムゾーン情報を取得します"

    @property
    def category(self) -> str:
        return "information"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="timezone",
                type="string",
                description="タイムゾーン（例：Asia/Tokyo, America/New_York, UTC）",
                required=False,
                default="Asia/Tokyo"
            ),
            ToolParameter(
                name="format",
                type="string",
                description="出力形式（datetime, date, time, timestamp）",
                required=False,
                default="datetime",
                enum=["datetime", "date", "time", "timestamp"]
            )
        ]

    async def _initialize_impl(self):
        """時刻ツールの初期化"""
        # よく使用されるタイムゾーンのマッピング
        self.timezone_mapping = {
            "日本": "Asia/Tokyo",
            "東京": "Asia/Tokyo",
            "JST": "Asia/Tokyo",
            "アメリカ": "America/New_York",
            "ニューヨーク": "America/New_York",
            "EST": "America/New_York",
            "EDT": "America/New_York",
            "ロンドン": "Europe/London",
            "GMT": "Europe/London",
            "UTC": "UTC",
            "協定世界時": "UTC",
            "北京": "Asia/Shanghai",
            "上海": "Asia/Shanghai",
            "香港": "Asia/Hong_Kong",
            "シドニー": "Australia/Sydney",
            "ロサンゼルス": "America/Los_Angeles",
            "PST": "America/Los_Angeles",
            "PDT": "America/Los_Angeles"
        }

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """時刻情報を取得して返す"""
        try:
            timezone_str = parameters.get("timezone", "Asia/Tokyo")
            format_type = parameters.get("format", "datetime")

            # タイムゾーン名の変換
            timezone_str = self.timezone_mapping.get(timezone_str, timezone_str)

            # タイムゾーンの設定
            try:
                tz = pytz.timezone(timezone_str)
            except pytz.UnknownTimeZoneError:
                # デフォルトにフォールバック
                logger.warning(f"Unknown timezone: {timezone_str}, using Asia/Tokyo")
                tz = pytz.timezone("Asia/Tokyo")
                timezone_str = "Asia/Tokyo"

            # 現在時刻を取得
            now = datetime.now(tz)

            # 指定された形式で時刻を整形
            if format_type == "datetime":
                time_info = self._format_datetime(now, timezone_str)
            elif format_type == "date":
                time_info = self._format_date(now)
            elif format_type == "time":
                time_info = self._format_time(now)
            elif format_type == "timestamp":
                time_info = self._format_timestamp(now)
            else:
                time_info = self._format_datetime(now, timezone_str)

            return ToolResult(
                success=True,
                result=time_info,
                metadata={
                    "timezone": timezone_str,
                    "format": format_type,
                    "timestamp": now.timestamp()
                }
            )

        except Exception as e:
            logger.error(f"Time tool execution failed: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=f"時刻情報の取得に失敗しました: {str(e)}"
            )

    def _format_datetime(self, dt: datetime, timezone_str: str) -> str:
        """日時の詳細フォーマット"""
        # 曜日の日本語変換
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[dt.weekday()]

        # 基本的な日時情報
        formatted = (
            f"📅 {dt.year}年{dt.month}月{dt.day}日（{weekday}曜日）\n"
            f"🕐 {dt.hour}時{dt.minute}分{dt.second}秒\n"
            f"🌍 タイムゾーン: {timezone_str}"
        )

        # 追加情報
        day_of_year = dt.timetuple().tm_yday
        week_number = dt.isocalendar()[1]

        formatted += (
            f"\n📊 年間通算: {day_of_year}日目"
            f"\n📈 週番号: 第{week_number}週"
        )

        # 特別な日付の判定
        special_info = self._get_special_date_info(dt)
        if special_info:
            formatted += f"\n🎉 {special_info}"

        return formatted

    def _format_date(self, dt: datetime) -> str:
        """日付のみのフォーマット"""
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[dt.weekday()]

        return f"{dt.year}年{dt.month}月{dt.day}日（{weekday}曜日）"

    def _format_time(self, dt: datetime) -> str:
        """時刻のみのフォーマット"""
        return f"{dt.hour}時{dt.minute}分{dt.second}秒"

    def _format_timestamp(self, dt: datetime) -> str:
        """タイムスタンプフォーマット"""
        unix_timestamp = int(dt.timestamp())
        iso_format = dt.isoformat()

        return (
            f"Unix タイムスタンプ: {unix_timestamp}\n"
            f"ISO形式: {iso_format}"
        )

    def _get_special_date_info(self, dt: datetime) -> str:
        """特別な日付情報を取得"""
        month = dt.month
        day = dt.day

        # 日本の祝日や記念日（簡易版）
        special_dates = {
            (1, 1): "元日",
            (2, 14): "バレンタインデー",
            (3, 14): "ホワイトデー",
            (4, 1): "エイプリルフール",
            (5, 5): "こどもの日",
            (7, 7): "七夕",
            (10, 31): "ハロウィン",
            (12, 24): "クリスマスイブ",
            (12, 25): "クリスマス",
            (12, 31): "大晦日"
        }

        return special_dates.get((month, day), "")

    async def get_world_clock(self) -> Dict[str, str]:
        """世界の主要都市の時刻を取得"""
        major_cities = {
            "東京": "Asia/Tokyo",
            "ニューヨーク": "America/New_York",
            "ロンドン": "Europe/London",
            "パリ": "Europe/Paris",
            "シドニー": "Australia/Sydney",
            "ロサンゼルス": "America/Los_Angeles",
            "北京": "Asia/Shanghai",
            "ドバイ": "Asia/Dubai"
        }

        world_times = {}
        for city, timezone_str in major_cities.items():
            try:
                tz = pytz.timezone(timezone_str)
                city_time = datetime.now(tz)
                world_times[city] = city_time.strftime("%H:%M")
            except Exception as e:
                logger.warning(f"Failed to get time for {city}: {e}")
                world_times[city] = "不明"

        return world_times

    async def calculate_time_difference(self, timezone1: str, timezone2: str) -> str:
        """2つのタイムゾーン間の時差を計算"""
        try:
            tz1 = pytz.timezone(self.timezone_mapping.get(timezone1, timezone1))
            tz2 = pytz.timezone(self.timezone_mapping.get(timezone2, timezone2))

            now = datetime.now()
            time1 = tz1.localize(now) if now.tzinfo is None else now.astimezone(tz1)
            time2 = tz2.localize(now) if now.tzinfo is None else now.astimezone(tz2)

            difference = time1.utcoffset() - time2.utcoffset()
            hours = difference.total_seconds() / 3600

            if hours > 0:
                return f"{timezone1}は{timezone2}より{hours:.1f}時間進んでいます"
            elif hours < 0:
                return f"{timezone1}は{timezone2}より{abs(hours):.1f}時間遅れています"
            else:
                return f"{timezone1}と{timezone2}は同じ時間帯です"

        except Exception as e:
            return f"時差の計算に失敗しました: {str(e)}"