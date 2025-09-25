"""
Weather Tool - 天気情報取得ツール

天気予報APIを使用して天気情報を取得するツール
"""

import os
import aiohttp
from typing import Dict, Any, List
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter


class WeatherTool(Tool):
    """天気情報を取得するツール"""

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "指定した地域の天気予報を取得します"

    @property
    def category(self) -> str:
        return "information"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="location",
                type="string",
                description="天気を調べる地域名（例：東京、大阪、札幌）",
                required=True
            ),
            ToolParameter(
                name="days",
                type="number",
                description="予報日数（1-5日、デフォルト：1日）",
                required=False,
                default=1
            )
        ]

    async def _initialize_impl(self):
        """天気APIの初期化"""
        # OpenWeatherMap API キーの確認
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not found, using mock weather data")

        self.base_url = "https://api.openweathermap.org/data/2.5"

        # 地域名の日英変換マップ
        self.location_map = {
            "東京": "Tokyo",
            "大阪": "Osaka",
            "京都": "Kyoto",
            "名古屋": "Nagoya",
            "札幌": "Sapporo",
            "福岡": "Fukuoka",
            "仙台": "Sendai",
            "広島": "Hiroshima",
            "新潟": "Niigata",
            "静岡": "Shizuoka",
            "横浜": "Yokohama",
            "神戸": "Kobe"
        }

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """天気情報を取得して返す"""
        try:
            location = parameters.get("location", "")
            days = int(parameters.get("days", 1))

            if not location:
                return ToolResult(
                    success=False,
                    result=None,
                    error="地域名が指定されていません"
                )

            # 日数の制限
            days = max(1, min(days, 5))

            # 地域名を英語に変換
            english_location = self.location_map.get(location, location)

            # API キーがある場合は実際のAPIを呼び出し
            if self.api_key:
                weather_data = await self._fetch_real_weather(english_location, days)
            else:
                # モックデータを返す
                weather_data = await self._fetch_mock_weather(location, days)

            return ToolResult(
                success=True,
                result=weather_data,
                metadata={
                    "location": location,
                    "days": days,
                    "source": "openweathermap" if self.api_key else "mock"
                }
            )

        except Exception as e:
            logger.error(f"Weather tool execution failed: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=f"天気情報の取得に失敗しました: {str(e)}"
            )

    async def _fetch_real_weather(self, location: str, days: int) -> str:
        """実際の天気APIから情報を取得"""
        try:
            async with aiohttp.ClientSession() as session:
                # 現在の天気を取得
                current_url = f"{self.base_url}/weather"
                current_params = {
                    "q": location,
                    "appid": self.api_key,
                    "units": "metric",
                    "lang": "ja"
                }

                async with session.get(current_url, params=current_params) as response:
                    if response.status != 200:
                        raise Exception(f"天気API error: {response.status}")

                    current_data = await response.json()

                # 予報データを取得（複数日の場合）
                forecast_data = None
                if days > 1:
                    forecast_url = f"{self.base_url}/forecast"
                    forecast_params = {
                        "q": location,
                        "appid": self.api_key,
                        "units": "metric",
                        "lang": "ja"
                    }

                    async with session.get(forecast_url, params=forecast_params) as response:
                        if response.status == 200:
                            forecast_data = await response.json()

                # データを整形
                return self._format_weather_data(current_data, forecast_data, days)

        except Exception as e:
            logger.error(f"Failed to fetch real weather data: {e}")
            raise

    async def _fetch_mock_weather(self, location: str, days: int) -> str:
        """モック天気データを生成"""
        import random

        weather_conditions = [
            ("晴れ", "☀️", "良い天気です"),
            ("曇り", "☁️", "雲が多めです"),
            ("雨", "🌧️", "傘をお持ちください"),
            ("雪", "❄️", "雪が降っています"),
            ("雷雨", "⛈️", "雷を伴う雨です")
        ]

        results = []
        for day in range(days):
            condition, emoji, description = random.choice(weather_conditions)
            temp = random.randint(5, 30)
            humidity = random.randint(40, 80)

            if day == 0:
                day_label = "今日"
            elif day == 1:
                day_label = "明日"
            else:
                day_label = f"{day + 1}日後"

            results.append(
                f"{day_label}の{location}の天気: {condition} {emoji}\n"
                f"気温: {temp}°C, 湿度: {humidity}%\n"
                f"{description}"
            )

        return "\n\n".join(results) + "\n\n※ これはデモ用のモックデータです"

    def _format_weather_data(self, current: Dict, forecast: Dict = None, days: int = 1) -> str:
        """天気データを読みやすい形式に整形"""
        result = []

        # 現在の天気
        location = current["name"]
        temp = round(current["main"]["temp"])
        feels_like = round(current["main"]["feels_like"])
        humidity = current["main"]["humidity"]
        weather_desc = current["weather"][0]["description"]
        weather_icon = self._get_weather_emoji(current["weather"][0]["id"])

        result.append(
            f"📍 {location}の現在の天気\n"
            f"{weather_icon} {weather_desc}\n"
            f"🌡️ 気温: {temp}°C (体感 {feels_like}°C)\n"
            f"💧 湿度: {humidity}%"
        )

        # 風速情報があれば追加
        if "wind" in current and "speed" in current["wind"]:
            wind_speed = round(current["wind"]["speed"] * 3.6, 1)  # m/s to km/h
            result.append(f"💨 風速: {wind_speed}km/h")

        # 予報データがあり、複数日の場合
        if forecast and days > 1:
            result.append("\n📅 予報:")

            # 日別予報を処理（簡略化）
            daily_forecasts = {}
            for item in forecast["list"][:days * 8]:  # 3時間ごとのデータ
                date = item["dt_txt"][:10]  # YYYY-MM-DD
                if date not in daily_forecasts:
                    daily_forecasts[date] = item

            for i, (date, forecast_item) in enumerate(daily_forecasts.items()):
                if i == 0:
                    continue  # 今日は既に表示済み

                temp_forecast = round(forecast_item["main"]["temp"])
                weather_forecast = forecast_item["weather"][0]["description"]
                emoji_forecast = self._get_weather_emoji(forecast_item["weather"][0]["id"])

                day_label = "明日" if i == 1 else f"{i + 1}日後"
                result.append(f"{day_label}: {emoji_forecast} {weather_forecast}, {temp_forecast}°C")

        return "\n".join(result)

    def _get_weather_emoji(self, weather_id: int) -> str:
        """天気IDに対応する絵文字を取得"""
        # OpenWeatherMap の weather condition codes
        if 200 <= weather_id <= 232:  # Thunderstorm
            return "⛈️"
        elif 300 <= weather_id <= 321:  # Drizzle
            return "🌦️"
        elif 500 <= weather_id <= 531:  # Rain
            return "🌧️"
        elif 600 <= weather_id <= 622:  # Snow
            return "❄️"
        elif 701 <= weather_id <= 781:  # Atmosphere
            return "🌫️"
        elif weather_id == 800:  # Clear sky
            return "☀️"
        elif 801 <= weather_id <= 804:  # Clouds
            return "☁️"
        else:
            return "🌤️"