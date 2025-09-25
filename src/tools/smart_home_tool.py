"""
Smart Home Tool - スマートホーム制御ツール

音声コマンドでHome Assistantを通じてスマートホームデバイスを制御するツール
"""

import re
from typing import Dict, Any, List, Optional
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter
from src.smart_home.home_assistant_client import HomeAssistantClient


class SmartHomeTool(Tool):
    """スマートホームデバイスを制御するツール"""

    def __init__(self):
        super().__init__()
        self.ha_client: Optional[HomeAssistantClient] = None

    @property
    def name(self) -> str:
        return "smart_home"

    @property
    def description(self) -> str:
        return "スマートホームデバイス（照明、エアコン、音楽プレーヤーなど）を制御します"

    @property
    def category(self) -> str:
        return "home_automation"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="実行するアクション",
                required=True,
                enum=["turn_on", "turn_off", "set_brightness", "set_temperature",
                      "play_music", "pause_music", "set_volume", "list_devices", "get_status"]
            ),
            ToolParameter(
                name="device_name",
                type="string",
                description="制御するデバイス名（例：リビングの照明、エアコン）",
                required=False
            ),
            ToolParameter(
                name="room",
                type="string",
                description="部屋名（例：リビング、寝室、キッチン）",
                required=False
            ),
            ToolParameter(
                name="value",
                type="number",
                description="設定値（明るさ：0-255、温度：度数、音量：0-100）",
                required=False
            )
        ]

    async def _initialize_impl(self):
        """スマートホームツールの初期化"""
        try:
            logger.info("Initializing Smart Home Tool...")

            # Home Assistantクライアントの初期化
            self.ha_client = HomeAssistantClient()
            await self.ha_client.initialize()

            logger.info("Smart Home Tool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Smart Home Tool: {e}")
            raise

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """スマートホーム制御を実行"""
        try:
            action = parameters.get("action", "").lower()
            device_name = parameters.get("device_name", "")
            room = parameters.get("room", "")
            value = parameters.get("value")

            if not action:
                return ToolResult(
                    success=False,
                    result=None,
                    error="アクションが指定されていません"
                )

            # アクション別の処理
            if action == "list_devices":
                return await self._list_devices()
            elif action == "get_status":
                return await self._get_device_status(device_name, room)
            elif action == "turn_on":
                return await self._turn_on_device(device_name, room, value)
            elif action == "turn_off":
                return await self._turn_off_device(device_name, room)
            elif action == "set_brightness":
                return await self._set_brightness(device_name, room, value)
            elif action == "set_temperature":
                return await self._set_temperature(device_name, room, value)
            elif action == "play_music":
                return await self._play_music(device_name, room)
            elif action == "pause_music":
                return await self._pause_music(device_name, room)
            elif action == "set_volume":
                return await self._set_volume(device_name, room, value)
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"サポートされていないアクション: {action}"
                )

        except Exception as e:
            logger.error(f"Smart Home tool execution failed: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=f"スマートホーム制御に失敗しました: {str(e)}"
            )

    async def _list_devices(self) -> ToolResult:
        """利用可能なデバイス一覧を取得"""
        try:
            devices = await self.ha_client.get_devices()

            if not devices:
                return ToolResult(
                    success=True,
                    result="🏠 利用可能なスマートホームデバイスが見つかりませんでした"
                )

            # ドメイン別にグループ化
            grouped_devices = {}
            for device in devices:
                domain = device["domain"]
                if domain not in grouped_devices:
                    grouped_devices[domain] = []
                grouped_devices[domain].append(device)

            # 結果を整形
            result_text = "🏠 利用可能なスマートホームデバイス:\n\n"

            domain_names = {
                "light": "💡 照明",
                "switch": "🔌 スイッチ",
                "climate": "❄️ エアコン・暖房",
                "media_player": "🎵 メディアプレーヤー",
                "cover": "🚪 カーテン・ブラインド",
                "fan": "🌀 ファン"
            }

            for domain, domain_devices in grouped_devices.items():
                domain_name = domain_names.get(domain, f"🔧 {domain}")
                result_text += f"{domain_name}:\n"

                for device in domain_devices:
                    name = device["friendly_name"]
                    state = device["state"]
                    result_text += f"  • {name} (状態: {state})\n"

                result_text += "\n"

            return ToolResult(
                success=True,
                result=result_text.strip(),
                metadata={"device_count": len(devices)}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"デバイス一覧の取得に失敗しました: {str(e)}"
            )

    async def _get_device_status(self, device_name: str, room: str) -> ToolResult:
        """デバイスの状態を取得"""
        try:
            entity_id = await self._find_device(device_name, room)
            if not entity_id:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"デバイスが見つかりませんでした: {device_name or room}"
                )

            device_state = await self.ha_client.get_device_state(entity_id)
            if not device_state:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"デバイスの状態を取得できませんでした: {entity_id}"
                )

            # 状態を整形
            friendly_name = device_state.get("friendly_name", entity_id)
            state = device_state.get("state", "不明")
            attributes = device_state.get("attributes", {})

            result_text = f"🔍 {friendly_name}の状態:\n"
            result_text += f"状態: {state}\n"

            # 属性の表示
            if "brightness" in attributes:
                brightness = attributes["brightness"]
                percentage = int((brightness / 255) * 100)
                result_text += f"明るさ: {percentage}%\n"

            if "temperature" in attributes:
                temp = attributes["temperature"]
                result_text += f"温度: {temp}°C\n"

            if "volume_level" in attributes:
                volume = attributes["volume_level"]
                percentage = int(volume * 100)
                result_text += f"音量: {percentage}%\n"

            return ToolResult(
                success=True,
                result=result_text.strip(),
                metadata={"entity_id": entity_id, "state": state}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"デバイス状態の取得に失敗しました: {str(e)}"
            )

    async def _turn_on_device(self, device_name: str, room: str, value: Any = None) -> ToolResult:
        """デバイスをオンにする"""
        try:
            entity_id = await self._find_device(device_name, room)
            if not entity_id:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"デバイスが見つかりませんでした: {device_name or room}"
                )

            kwargs = {}
            if value is not None:
                # 照明の場合は明るさを設定
                if entity_id.startswith("light."):
                    # 0-100の値を0-255に変換
                    brightness = min(255, max(0, int(float(value) * 255 / 100)))
                    kwargs["brightness"] = brightness

            success = await self.ha_client.turn_on_device(entity_id, **kwargs)

            if success:
                friendly_name = self.ha_client.device_cache.get(entity_id, {}).get("friendly_name", entity_id)
                result_text = f"✅ {friendly_name}をオンにしました"

                if "brightness" in kwargs:
                    percentage = int((kwargs["brightness"] / 255) * 100)
                    result_text += f"（明るさ: {percentage}%）"

                return ToolResult(
                    success=True,
                    result=result_text,
                    metadata={"entity_id": entity_id, "action": "turn_on"}
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error="デバイスのオンに失敗しました"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"デバイスの制御に失敗しました: {str(e)}"
            )

    async def _turn_off_device(self, device_name: str, room: str) -> ToolResult:
        """デバイスをオフにする"""
        try:
            entity_id = await self._find_device(device_name, room)
            if not entity_id:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"デバイスが見つかりませんでした: {device_name or room}"
                )

            success = await self.ha_client.turn_off_device(entity_id)

            if success:
                friendly_name = self.ha_client.device_cache.get(entity_id, {}).get("friendly_name", entity_id)
                return ToolResult(
                    success=True,
                    result=f"✅ {friendly_name}をオフにしました",
                    metadata={"entity_id": entity_id, "action": "turn_off"}
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error="デバイスのオフに失敗しました"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"デバイスの制御に失敗しました: {str(e)}"
            )

    async def _set_brightness(self, device_name: str, room: str, value: Any) -> ToolResult:
        """照明の明るさを設定"""
        try:
            if value is None:
                return ToolResult(
                    success=False,
                    result=None,
                    error="明るさの値が指定されていません"
                )

            entity_id = await self._find_device(device_name, room, device_type="light")
            if not entity_id:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"照明が見つかりませんでした: {device_name or room}"
                )

            # 0-100の値を0-255に変換
            brightness = min(255, max(0, int(float(value) * 255 / 100)))
            success = await self.ha_client.set_brightness(entity_id, brightness)

            if success:
                friendly_name = self.ha_client.device_cache.get(entity_id, {}).get("friendly_name", entity_id)
                return ToolResult(
                    success=True,
                    result=f"✅ {friendly_name}の明るさを{int(value)}%に設定しました",
                    metadata={"entity_id": entity_id, "brightness": brightness}
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error="明るさの設定に失敗しました"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"明るさの設定に失敗しました: {str(e)}"
            )

    async def _set_temperature(self, device_name: str, room: str, value: Any) -> ToolResult:
        """エアコンの温度を設定"""
        try:
            if value is None:
                return ToolResult(
                    success=False,
                    result=None,
                    error="温度の値が指定されていません"
                )

            entity_id = await self._find_device(device_name, room, device_type="climate")
            if not entity_id:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"エアコンが見つかりませんでした: {device_name or room}"
                )

            temperature = float(value)
            success = await self.ha_client.set_temperature(entity_id, temperature)

            if success:
                friendly_name = self.ha_client.device_cache.get(entity_id, {}).get("friendly_name", entity_id)
                return ToolResult(
                    success=True,
                    result=f"🌡️ {friendly_name}の温度を{temperature}°Cに設定しました",
                    metadata={"entity_id": entity_id, "temperature": temperature}
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error="温度の設定に失敗しました"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"温度の設定に失敗しました: {str(e)}"
            )

    async def _play_music(self, device_name: str, room: str) -> ToolResult:
        """音楽を再生"""
        try:
            entity_id = await self._find_device(device_name, room, device_type="media_player")
            if not entity_id:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"メディアプレーヤーが見つかりませんでした: {device_name or room}"
                )

            success = await self.ha_client.play_media(entity_id)

            if success:
                friendly_name = self.ha_client.device_cache.get(entity_id, {}).get("friendly_name", entity_id)
                return ToolResult(
                    success=True,
                    result=f"🎵 {friendly_name}で音楽を再生しました",
                    metadata={"entity_id": entity_id, "action": "play"}
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error="音楽の再生に失敗しました"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"音楽の再生に失敗しました: {str(e)}"
            )

    async def _pause_music(self, device_name: str, room: str) -> ToolResult:
        """音楽を一時停止"""
        try:
            entity_id = await self._find_device(device_name, room, device_type="media_player")
            if not entity_id:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"メディアプレーヤーが見つかりませんでした: {device_name or room}"
                )

            success = await self.ha_client.pause_media(entity_id)

            if success:
                friendly_name = self.ha_client.device_cache.get(entity_id, {}).get("friendly_name", entity_id)
                return ToolResult(
                    success=True,
                    result=f"⏸️ {friendly_name}の音楽を一時停止しました",
                    metadata={"entity_id": entity_id, "action": "pause"}
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error="音楽の一時停止に失敗しました"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"音楽の一時停止に失敗しました: {str(e)}"
            )

    async def _set_volume(self, device_name: str, room: str, value: Any) -> ToolResult:
        """音量を設定"""
        try:
            if value is None:
                return ToolResult(
                    success=False,
                    result=None,
                    error="音量の値が指定されていません"
                )

            entity_id = await self._find_device(device_name, room, device_type="media_player")
            if not entity_id:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"メディアプレーヤーが見つかりませんでした: {device_name or room}"
                )

            # 0-100の値を0.0-1.0に変換
            volume = min(1.0, max(0.0, float(value) / 100))
            success = await self.ha_client.set_volume(entity_id, volume)

            if success:
                friendly_name = self.ha_client.device_cache.get(entity_id, {}).get("friendly_name", entity_id)
                return ToolResult(
                    success=True,
                    result=f"🔊 {friendly_name}の音量を{int(value)}%に設定しました",
                    metadata={"entity_id": entity_id, "volume": volume}
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error="音量の設定に失敗しました"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"音量の設定に失敗しました: {str(e)}"
            )

    async def _find_device(self, device_name: str, room: str, device_type: str = None) -> Optional[str]:
        """デバイス名または部屋名からentity_idを検索"""
        try:
            # デバイス名が指定されている場合
            if device_name:
                entity_id = await self.ha_client.find_device_by_name(device_name)
                if entity_id:
                    # デバイスタイプのチェック
                    if device_type and not entity_id.startswith(f"{device_type}."):
                        # タイプが一致しない場合は他の候補を探す
                        pass
                    else:
                        return entity_id

            # 部屋名が指定されている場合
            if room:
                room_devices = await self.ha_client.get_room_devices(room)

                # デバイスタイプで絞り込み
                if device_type:
                    filtered_devices = [d for d in room_devices if d.startswith(f"{device_type}.")]
                    if filtered_devices:
                        return filtered_devices[0]  # 最初の候補を返す
                else:
                    if room_devices:
                        return room_devices[0]  # 最初の候補を返す

            return None

        except Exception as e:
            logger.error(f"Device search failed: {e}")
            return None

    async def _cleanup_impl(self):
        """クリーンアップ処理"""
        if self.ha_client:
            await self.ha_client.cleanup()
            self.ha_client = None