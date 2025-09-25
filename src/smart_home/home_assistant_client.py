"""
Home Assistant Client - スマートホーム連携

Home Assistantとの連携によってスマートホームデバイスを制御するクライアント
"""

import os
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class HomeAssistantClient:
    """
    Home Assistantとの連携クライアント

    音声コマンドでライト、エアコン、音楽などのスマートホームデバイスを制御
    """

    def __init__(self):
        self.base_url = ""
        self.token = ""
        self.is_initialized = False
        self.session = None

        # デバイス状態のキャッシュ
        self.device_cache = {}
        self.last_cache_update = None

    async def initialize(self):
        """Home Assistantクライアントの初期化"""
        try:
            logger.info("Initializing Home Assistant client...")

            # 環境変数から設定を読み込み
            self.base_url = os.getenv("HOME_ASSISTANT_URL", "http://localhost:8123")
            self.token = os.getenv("HOME_ASSISTANT_TOKEN", "")

            if not self.token:
                logger.warning("Home Assistant token not configured, using mock mode")
                self.mock_mode = True
            else:
                self.mock_mode = False

                # HTTPセッションの作成
                timeout = aiohttp.ClientTimeout(total=10)
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
                self.session = aiohttp.ClientSession(
                    timeout=timeout,
                    headers=headers
                )

                # 接続テスト
                await self._test_connection()

            # デバイス情報の初期読み込み
            await self.refresh_device_cache()

            self.is_initialized = True
            logger.info(f"Home Assistant client initialized (mock: {self.mock_mode})")

        except Exception as e:
            logger.error(f"Failed to initialize Home Assistant client: {e}")
            self.mock_mode = True
            self.is_initialized = True  # モックモードでも動作させる

    async def _test_connection(self):
        """Home Assistantへの接続テスト"""
        try:
            url = f"{self.base_url}/api/"
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Connection test failed: {response.status}")

                data = await response.json()
                logger.info(f"Connected to Home Assistant: {data.get('message', 'Unknown')}")

        except Exception as e:
            logger.error(f"Home Assistant connection test failed: {e}")
            raise

    async def get_devices(self) -> List[Dict[str, Any]]:
        """利用可能なデバイス一覧を取得"""
        if not self.is_initialized:
            return []

        try:
            if self.mock_mode:
                return await self._get_mock_devices()

            url = f"{self.base_url}/api/states"
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to get devices: {response.status}")
                    return []

                devices_data = await response.json()
                devices = []

                for device in devices_data:
                    entity_id = device.get("entity_id", "")
                    domain = entity_id.split(".")[0]

                    # 制御可能なドメインのみを対象
                    if domain in ["light", "switch", "climate", "media_player", "cover", "fan"]:
                        devices.append({
                            "entity_id": entity_id,
                            "domain": domain,
                            "friendly_name": device.get("attributes", {}).get("friendly_name", entity_id),
                            "state": device.get("state", "unknown"),
                            "attributes": device.get("attributes", {})
                        })

                return devices

        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            return []

    async def _get_mock_devices(self) -> List[Dict[str, Any]]:
        """モックデバイス一覧を生成"""
        return [
            {
                "entity_id": "light.living_room",
                "domain": "light",
                "friendly_name": "リビングの照明",
                "state": "off",
                "attributes": {"brightness": 0, "color_mode": "brightness"}
            },
            {
                "entity_id": "light.bedroom",
                "domain": "light",
                "friendly_name": "寝室の照明",
                "state": "off",
                "attributes": {"brightness": 0, "color_mode": "rgb"}
            },
            {
                "entity_id": "switch.coffee_maker",
                "domain": "switch",
                "friendly_name": "コーヒーメーカー",
                "state": "off",
                "attributes": {}
            },
            {
                "entity_id": "climate.living_room_ac",
                "domain": "climate",
                "friendly_name": "リビングエアコン",
                "state": "off",
                "attributes": {"temperature": 22, "target_temp_high": 25, "target_temp_low": 20}
            },
            {
                "entity_id": "media_player.spotify",
                "domain": "media_player",
                "friendly_name": "Spotify",
                "state": "idle",
                "attributes": {"volume_level": 0.5, "source": "Spotify"}
            }
        ]

    async def turn_on_device(self, entity_id: str, **kwargs) -> bool:
        """デバイスを電源オン"""
        return await self._call_service("turn_on", entity_id, **kwargs)

    async def turn_off_device(self, entity_id: str) -> bool:
        """デバイスを電源オフ"""
        return await self._call_service("turn_off", entity_id)

    async def set_brightness(self, entity_id: str, brightness: int) -> bool:
        """照明の明るさを設定（0-255）"""
        return await self._call_service("turn_on", entity_id, brightness=brightness)

    async def set_temperature(self, entity_id: str, temperature: float) -> bool:
        """エアコンの温度を設定"""
        return await self._call_service("set_temperature", entity_id, temperature=temperature)

    async def play_media(self, entity_id: str, media_url: str = None) -> bool:
        """メディアを再生"""
        if media_url:
            return await self._call_service("play_media", entity_id,
                                           media_content_id=media_url,
                                           media_content_type="music")
        else:
            return await self._call_service("media_play", entity_id)

    async def pause_media(self, entity_id: str) -> bool:
        """メディアを一時停止"""
        return await self._call_service("media_pause", entity_id)

    async def set_volume(self, entity_id: str, volume: float) -> bool:
        """音量を設定（0.0-1.0）"""
        return await self._call_service("volume_set", entity_id, volume_level=volume)

    async def _call_service(self, service: str, entity_id: str, **kwargs) -> bool:
        """Home Assistantサービスを呼び出し"""
        try:
            domain = entity_id.split(".")[0]

            if self.mock_mode:
                return await self._mock_service_call(service, entity_id, **kwargs)

            url = f"{self.base_url}/api/services/{domain}/{service}"
            data = {"entity_id": entity_id}
            data.update(kwargs)

            async with self.session.post(url, json=data) as response:
                if response.status in [200, 201]:
                    logger.info(f"Service call successful: {service} on {entity_id}")

                    # キャッシュを更新
                    await self._update_device_cache(entity_id)
                    return True
                else:
                    logger.error(f"Service call failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Service call error: {e}")
            return False

    async def _mock_service_call(self, service: str, entity_id: str, **kwargs) -> bool:
        """モックサービス呼び出し"""
        logger.info(f"Mock service call: {service} on {entity_id} with {kwargs}")

        # モックデバイス状態を更新
        if entity_id not in self.device_cache:
            self.device_cache[entity_id] = {"state": "unknown", "attributes": {}}

        device = self.device_cache[entity_id]

        if service == "turn_on":
            device["state"] = "on"
            if "brightness" in kwargs:
                device["attributes"]["brightness"] = kwargs["brightness"]
        elif service == "turn_off":
            device["state"] = "off"
            device["attributes"]["brightness"] = 0
        elif service == "set_temperature":
            device["attributes"]["temperature"] = kwargs.get("temperature", 22)
        elif service == "media_play":
            device["state"] = "playing"
        elif service == "media_pause":
            device["state"] = "paused"
        elif service == "volume_set":
            device["attributes"]["volume_level"] = kwargs.get("volume_level", 0.5)

        return True

    async def _update_device_cache(self, entity_id: str):
        """特定デバイスのキャッシュを更新"""
        try:
            if self.mock_mode:
                return

            url = f"{self.base_url}/api/states/{entity_id}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    device_data = await response.json()
                    self.device_cache[entity_id] = {
                        "state": device_data.get("state", "unknown"),
                        "attributes": device_data.get("attributes", {})
                    }

        except Exception as e:
            logger.error(f"Failed to update device cache: {e}")

    async def refresh_device_cache(self):
        """全デバイスのキャッシュを更新"""
        try:
            devices = await self.get_devices()
            self.device_cache = {}

            for device in devices:
                self.device_cache[device["entity_id"]] = {
                    "state": device["state"],
                    "attributes": device["attributes"],
                    "friendly_name": device["friendly_name"],
                    "domain": device["domain"]
                }

            self.last_cache_update = datetime.now()
            logger.debug(f"Device cache updated with {len(devices)} devices")

        except Exception as e:
            logger.error(f"Failed to refresh device cache: {e}")

    async def get_device_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """デバイスの現在状態を取得"""
        if entity_id in self.device_cache:
            return self.device_cache[entity_id].copy()

        # キャッシュにない場合は個別に取得
        await self._update_device_cache(entity_id)
        return self.device_cache.get(entity_id)

    async def find_device_by_name(self, name: str) -> Optional[str]:
        """デバイス名からentity_idを検索"""
        name_lower = name.lower()

        for entity_id, device_info in self.device_cache.items():
            friendly_name = device_info.get("friendly_name", "").lower()

            # 完全一致
            if name_lower == friendly_name:
                return entity_id

            # 部分一致
            if name_lower in friendly_name or friendly_name in name_lower:
                return entity_id

        # entity_id自体での検索
        for entity_id in self.device_cache.keys():
            if name_lower in entity_id.lower():
                return entity_id

        return None

    async def get_room_devices(self, room_name: str) -> List[str]:
        """部屋名に基づいてデバイスを検索"""
        room_lower = room_name.lower()
        room_devices = []

        room_keywords = {
            "リビング": ["living", "リビング", "居間"],
            "寝室": ["bedroom", "寝室", "ベッドルーム"],
            "キッチン": ["kitchen", "キッチン", "台所"],
            "洗面所": ["bathroom", "洗面所", "バスルーム"],
            "書斎": ["study", "書斎", "オフィス"],
        }

        # 部屋名のマッピング
        keywords = room_keywords.get(room_name, [room_lower])

        for entity_id, device_info in self.device_cache.items():
            friendly_name = device_info.get("friendly_name", "").lower()

            for keyword in keywords:
                if keyword in friendly_name or keyword in entity_id.lower():
                    room_devices.append(entity_id)
                    break

        return room_devices

    def get_status(self) -> Dict[str, Any]:
        """クライアントの状態を取得"""
        return {
            "initialized": self.is_initialized,
            "mock_mode": getattr(self, "mock_mode", True),
            "base_url": self.base_url,
            "cached_devices": len(self.device_cache),
            "last_cache_update": self.last_cache_update.isoformat() if self.last_cache_update else None
        }

    async def cleanup(self):
        """リソースのクリーンアップ"""
        logger.info("Cleaning up Home Assistant client...")

        if self.session:
            await self.session.close()
            self.session = None

        self.device_cache.clear()
        self.is_initialized = False

        logger.info("Home Assistant client cleanup completed")