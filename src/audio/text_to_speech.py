"""
Text-to-Speech - 音声合成システム

ElevenLabsとブラウザTTSを使用した高品質音声合成の実装
"""

import os
import asyncio
import aiofiles
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

try:
    from elevenlabs import Voice, VoiceSettings, generate, save
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    logger.warning("ElevenLabs not available, using fallback TTS")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not available")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available")

import tempfile


class TextToSpeech:
    """テキストを音声に変換するクラス"""

    def __init__(self):
        self.elevenlabs_client = None
        self.is_initialized = False
        self.audio_cache = {}  # 音声キャッシュ
        self.config = {
            "provider": "openai",  # openai, gtts, browser
            "voice_id": "default",
            "voice": "alloy",  # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
            "model": "eleven_monolingual_v1",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
            "language": "ja",
            "cache_enabled": True,
            "output_directory": "./data/audio"
        }

    async def initialize(self):
        """TTSシステムの初期化"""
        try:
            logger.info("Initializing Text-to-Speech...")

            # 環境変数から設定を読み込み
            elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
            voice_id = os.getenv("ELEVENLABS_VOICE_ID", self.config["voice_id"])
            provider = os.getenv("TTS_PROVIDER", self.config["provider"]).lower()

            self.config.update({
                "provider": provider,
                "voice_id": voice_id
            })

            # 出力ディレクトリの作成
            os.makedirs(self.config["output_directory"], exist_ok=True)

            # プロバイダーの初期化
            if provider == "elevenlabs" and elevenlabs_api_key and ELEVENLABS_AVAILABLE:
                logger.info("Initializing ElevenLabs TTS")
                self.elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)

                # 音声リストの取得とデフォルト音声の設定
                await self._initialize_elevenlabs()

            elif provider == "openai" and os.getenv("OPENAI_API_KEY") and OPENAI_AVAILABLE:
                logger.info("Initializing OpenAI TTS")
                self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            elif provider == "gtts" and GTTS_AVAILABLE:
                logger.info("Using Google TTS (gTTS)")

            else:
                logger.info("Using browser TTS fallback")
                self.config["provider"] = "browser"

            self.is_initialized = True
            logger.info(f"Text-to-Speech initialized with provider: {self.config['provider']}")

        except Exception as e:
            logger.error(f"Failed to initialize Text-to-Speech: {e}")
            raise

    async def _initialize_elevenlabs(self):
        """ElevenLabsの初期化"""
        try:
            # 利用可能な音声の取得
            voices = self.elevenlabs_client.voices.get_all()

            if voices.voices:
                # デフォルト音声の設定
                if self.config["voice_id"] == "default":
                    self.config["voice_id"] = voices.voices[0].voice_id
                    logger.info(f"Using default voice: {voices.voices[0].name}")

                # 指定された音声IDの確認
                voice_found = False
                for voice in voices.voices:
                    if voice.voice_id == self.config["voice_id"]:
                        voice_found = True
                        logger.info(f"Using voice: {voice.name} ({voice.voice_id})")
                        break

                if not voice_found:
                    logger.warning(f"Voice ID {self.config['voice_id']} not found, using default")
                    self.config["voice_id"] = voices.voices[0].voice_id

        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs voices: {e}")
            raise

    async def synthesize(self, text: str) -> str:
        """
        テキストを音声に変換

        Args:
            text: 合成するテキスト

        Returns:
            生成された音声ファイルのURL
        """
        if not self.is_initialized:
            raise RuntimeError("Text-to-Speech not initialized")

        if not text.strip():
            logger.warning("Empty text provided for synthesis")
            return ""

        try:
            logger.info(f"Synthesizing text: {text[:50]}...")

            # キャッシュチェック
            if self.config["cache_enabled"]:
                cached_url = await self._get_cached_audio(text)
                if cached_url:
                    logger.debug("Using cached audio")
                    return cached_url

            # プロバイダー別の音声合成
            audio_path = None
            if self.config["provider"] == "elevenlabs" and self.elevenlabs_client:
                audio_path = await self._synthesize_elevenlabs(text)
            elif self.config["provider"] == "openai" and hasattr(self, 'openai_client'):
                audio_path = await self._synthesize_openai(text)
            elif self.config["provider"] == "gtts" and GTTS_AVAILABLE:
                audio_path = await self._synthesize_gtts(text)
            else:
                # ブラウザTTSの場合は空文字列を返す（クライアントサイドで処理）
                return ""

            if audio_path:
                # 相対URLに変換（dataディレクトリベース）
                relative_path = os.path.relpath(audio_path, "./data")
                audio_url = f"/data/{relative_path.replace(os.sep, '/')}"

                # キャッシュに保存
                if self.config["cache_enabled"]:
                    await self._cache_audio(text, audio_url)

                logger.info(f"Audio synthesized: {audio_url}")
                return audio_url

            return ""

        except Exception as e:
            logger.error(f"Text-to-speech synthesis failed: {e}")
            return ""

    async def _synthesize_elevenlabs(self, text: str) -> Optional[str]:
        """ElevenLabsによる音声合成"""
        try:
            # 音声設定
            voice_settings = VoiceSettings(
                stability=self.config["stability"],
                similarity_boost=self.config["similarity_boost"],
                style=self.config["style"],
                use_speaker_boost=self.config["use_speaker_boost"]
            )

            # 音声生成
            audio = generate(
                text=text,
                voice=Voice(voice_id=self.config["voice_id"]),
                voice_settings=voice_settings,
                model=self.config["model"]
            )

            # ファイルに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"tts_{timestamp}.mp3"
            audio_path = os.path.join(self.config["output_directory"], filename)

            # 音声データを保存
            async with aiofiles.open(audio_path, 'wb') as f:
                await f.write(audio)

            return audio_path

        except Exception as e:
            logger.error(f"ElevenLabs synthesis failed: {e}")
            raise

    async def _synthesize_gtts(self, text: str) -> Optional[str]:
        """Google TTSによる音声合成"""
        try:
            # gTTSオブジェクトの作成
            tts = gTTS(text=text, lang=self.config["language"], slow=False)

            # ファイルに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"tts_{timestamp}.mp3"
            audio_path = os.path.join(self.config["output_directory"], filename)

            # 非同期でファイルを保存
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name

            # gTTSで一時ファイルに保存
            await asyncio.get_event_loop().run_in_executor(
                None, tts.save, temp_path
            )

            # 最終的な場所に移動
            os.rename(temp_path, audio_path)

            return audio_path

        except Exception as e:
            logger.error(f"gTTS synthesis failed: {e}")
            raise

    async def _get_cached_audio(self, text: str) -> Optional[str]:
        """キャッシュされた音声を取得"""
        text_hash = hash(text + self.config["voice_id"])
        return self.audio_cache.get(text_hash)

    async def _cache_audio(self, text: str, audio_url: str):
        """音声をキャッシュに保存"""
        text_hash = hash(text + self.config["voice_id"])
        self.audio_cache[text_hash] = audio_url

        # キャッシュサイズ制限（1000エントリー）
        if len(self.audio_cache) > 1000:
            # 古いエントリーを削除（簡易的な実装）
            oldest_key = next(iter(self.audio_cache))
            del self.audio_cache[oldest_key]

    async def get_available_voices(self) -> Dict[str, Any]:
        """利用可能な音声リストを取得"""
        if not self.is_initialized:
            return {"voices": []}

        try:
            if self.config["provider"] == "elevenlabs" and self.elevenlabs_client:
                voices = self.elevenlabs_client.voices.get_all()
                return {
                    "voices": [
                        {
                            "id": voice.voice_id,
                            "name": voice.name,
                            "category": voice.category,
                            "labels": voice.labels
                        }
                        for voice in voices.voices
                    ]
                }
            else:
                return {"voices": [{"id": "default", "name": "Default"}]}

        except Exception as e:
            logger.error(f"Failed to get available voices: {e}")
            return {"voices": []}

    async def get_status(self) -> Dict[str, Any]:
        """TTSシステムの状態を取得"""
        return {
            "initialized": self.is_initialized,
            "provider": self.config["provider"],
            "voice_id": self.config["voice_id"],
            "language": self.config["language"],
            "cache_size": len(self.audio_cache),
            "cache_enabled": self.config["cache_enabled"]
        }

    async def update_config(self, config: Dict[str, Any]):
        """設定を更新"""
        logger.info(f"Updating TTS config: {config}")
        old_config = self.config.copy()
        self.config.update(config)

        # プロバイダーまたは音声が変更された場合はキャッシュをクリア
        if (old_config.get("provider") != self.config.get("provider") or
            old_config.get("voice_id") != self.config.get("voice_id")):
            logger.info("Provider or voice changed, clearing cache...")
            self.audio_cache.clear()

        # プロバイダーが変更された場合は再初期化
        if old_config.get("provider") != self.config.get("provider"):
            logger.info("Provider changed, reinitializing...")
            await self.cleanup()
            await self.initialize()

    async def clear_cache(self):
        """音声キャッシュをクリア"""
        logger.info("Clearing TTS cache...")
        self.audio_cache.clear()

        # ディスク上のキャッシュファイルも削除
        try:
            for filename in os.listdir(self.config["output_directory"]):
                if filename.startswith("tts_"):
                    file_path = os.path.join(self.config["output_directory"], filename)
                    os.remove(file_path)
            logger.info("Disk cache cleared")
        except Exception as e:
            logger.warning(f"Failed to clear disk cache: {e}")

    async def _synthesize_openai(self, text: str) -> Optional[str]:
        """OpenAI TTSによる音声合成"""
        try:
            logger.debug(f"Synthesizing with OpenAI TTS: {text[:50]}...")

            # OpenAI TTS API呼び出し
            voice = self.config.get("voice", "alloy")
            speed = self.config.get("speed", 1.2)  # デフォルト1.2倍速
            response = self.openai_client.audio.speech.create(
                model="tts-1",  # tts-1 または tts-1-hd
                voice=voice,  # alloy, echo, fable, onyx, nova, shimmer
                input=text,
                speed=speed,  # 0.25 ~ 4.0 (デフォルト1.0)
                response_format="mp3"
            )

            # ファイルに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"tts_openai_{timestamp}.mp3"
            audio_path = os.path.join(self.config["output_directory"], filename)

            # 音声データを保存
            with open(audio_path, 'wb') as f:
                f.write(response.content)

            logger.debug(f"OpenAI TTS audio saved to: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"OpenAI TTS synthesis failed: {e}")
            raise

    async def cleanup(self):
        """リソースのクリーンアップ"""
        logger.info("Cleaning up Text-to-Speech...")

        self.elevenlabs_client = None
        if hasattr(self, 'openai_client'):
            self.openai_client = None
        self.audio_cache.clear()
        self.is_initialized = False

        logger.info("Text-to-Speech cleanup completed")