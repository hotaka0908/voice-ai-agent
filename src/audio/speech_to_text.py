"""
Speech-to-Text - 音声認識システム

Whisperを使用した高精度音声認識の実装
"""

import os
import io
import wave
import tempfile
from typing import Optional, Dict, Any, Union
import numpy as np
from loguru import logger

try:
    import whisper
except ImportError:
    whisper = None
    logger.warning("Whisper not available, using OpenAI API fallback")

try:
    import openai
except ImportError:
    openai = None

try:
    import pyaudio
except ImportError:
    pyaudio = None
    logger.warning("PyAudio not available, audio recording disabled")


class SpeechToText:
    """音声をテキストに変換するクラス"""

    def __init__(self):
        self.whisper_model = None
        self.openai_client = None
        self.is_initialized = False
        self.config = {
            "model": "base",  # tiny, base, small, medium, large
            "language": "ja",
            "use_local": True,  # ローカルWhisperを使用するか
            "sample_rate": 16000,
            "chunk_duration": 30  # 秒
        }

    async def initialize(self):
        """STTシステムの初期化"""
        try:
            logger.info("Initializing Speech-to-Text...")

            # 環境変数から設定を読み込み
            openai_api_key = os.getenv("OPENAI_API_KEY")
            model_name = os.getenv("WHISPER_MODEL", self.config["model"])
            use_local = os.getenv("USE_LOCAL_WHISPER", "true").lower() == "true"

            self.config.update({
                "model": model_name,
                "use_local": use_local and whisper is not None
            })

            if self.config["use_local"] and whisper:
                # ローカルWhisperモデルの初期化
                logger.info(f"Loading local Whisper model: {model_name}")
                self.whisper_model = whisper.load_model(model_name)
                logger.info("Local Whisper model loaded successfully")

            elif openai_api_key:
                # OpenAI API の初期化
                logger.info("Initializing OpenAI Whisper API")
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                logger.info("OpenAI Whisper API initialized")

            else:
                raise ValueError("No valid STT provider available")

            self.is_initialized = True
            logger.info("Speech-to-Text initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Speech-to-Text: {e}")
            raise

    async def transcribe(self, audio_data: bytes) -> str:
        """
        音声データをテキストに変換

        Args:
            audio_data: WAV形式の音声データ

        Returns:
            認識されたテキスト
        """
        if not self.is_initialized:
            raise RuntimeError("Speech-to-Text not initialized")

        try:
            logger.debug(f"Transcribing audio data: {len(audio_data)} bytes")

            # 音声データの検証と前処理
            processed_audio = self._preprocess_audio(audio_data)
            if processed_audio is None:
                logger.warning("Audio data is too short or invalid")
                return ""

            # 音声認識の実行（データ型に応じて処理分岐）
            if isinstance(processed_audio, bytes):
                # WebM等のraw形式はOpenAI APIに直接送信
                text = await self._transcribe_openai_raw(processed_audio)
            elif self.config["use_local"] and self.whisper_model:
                text = await self._transcribe_local(processed_audio)
            elif self.openai_client:
                text = await self._transcribe_openai(processed_audio)
            else:
                raise RuntimeError("No STT provider available")

            logger.info(f"Transcription result: {text}")
            return text.strip()

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return ""

    def _preprocess_audio(self, audio_data: bytes) -> Optional[Union[np.ndarray, bytes]]:
        """音声データの前処理"""
        try:
            # 音声データ形式の検出
            if audio_data[:4] == b'RIFF':
                # WAVファイルとして読み込み
                audio_io = io.BytesIO(audio_data)
                with wave.open(audio_io, 'rb') as wav_file:
                    # 基本情報を取得
                    sample_rate = wav_file.getframerate()
                    n_channels = wav_file.getnchannels()
                    n_frames = wav_file.getnframes()

                    # 音声データを読み込み
                    frames = wav_file.readframes(n_frames)
                    audio_np = np.frombuffer(frames, dtype=np.int16)

                    # ステレオの場合はモノラルに変換
                    logger.debug(f"Number of channels: {n_channels}, type: {type(n_channels)}")
                    if int(n_channels) == 2:
                        audio_np = audio_np.reshape(-1, 2).mean(axis=1)

                    # サンプリングレートを16kHzに統一
                    logger.debug(f"Sample rate: {sample_rate}, type: {type(sample_rate)}")
                    if int(sample_rate) != self.config["sample_rate"]:
                        audio_np = self._resample_audio(
                            audio_np, sample_rate, self.config["sample_rate"]
                        )

                    # 音声の正規化
                    audio_np = audio_np.astype(np.float32) / 32768.0

                    # 最小長チェック（0.5秒以上）
                    min_samples = int(self.config["sample_rate"] * 0.5)
                    if audio_np.size < min_samples:
                        return None

                    return audio_np
            else:
                # WebM/その他の形式の場合は、直接OpenAI APIに送る
                logger.debug(f"Non-WAV audio format detected, using direct API call")
                return self._preprocess_raw_audio(audio_data)

        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            return None

    def _preprocess_raw_audio(self, audio_data: bytes) -> bytes:
        """WebM/その他の生音声データの処理（OpenAI API用）"""
        # WebM等の形式はOpenAI APIに直接送信するためbytesとして返す
        logger.debug(f"Processing raw audio data: {len(audio_data)} bytes")
        return audio_data

    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """音声のリサンプリング（簡易版）"""
        # 簡単なリサンプリング実装
        # 本格的な実装にはlibrosasampleimpactを使用することを推奨
        if orig_sr == target_sr:
            return audio

        # 線形補間によるリサンプリング
        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio)

    async def _transcribe_local(self, audio_data: np.ndarray) -> str:
        """ローカルWhisperによる音声認識"""
        try:
            # Whisperで音声認識実行
            result = self.whisper_model.transcribe(
                audio_data,
                language=self.config["language"],
                task="transcribe"
            )

            return result["text"]

        except Exception as e:
            logger.error(f"Local Whisper transcription failed: {e}")
            raise

    async def _transcribe_openai_raw(self, audio_data: bytes) -> str:
        """OpenAI APIによる音声認識（生バイナリデータ用）"""
        try:
            # 一時ファイルに音声データを保存
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            try:
                # OpenAI APIで音声認識
                with open(temp_path, "rb") as audio_file:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=self.config["language"]
                    )

                return transcript.text

            finally:
                # 一時ファイルを削除
                os.unlink(temp_path)

        except Exception as e:
            logger.error(f"OpenAI Whisper raw transcription failed: {e}")
            raise

    async def _transcribe_openai(self, audio_data: np.ndarray) -> str:
        """OpenAI APIによる音声認識"""
        try:
            # 一時ファイルに音声を保存
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                # NumPy配列をWAVファイルに変換
                audio_int16 = (audio_data * 32767).astype(np.int16)
                with wave.open(temp_file, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(self.config["sample_rate"])
                    wav_file.writeframes(audio_int16.tobytes())

                temp_path = temp_file.name

            try:
                # OpenAI APIで音声認識
                with open(temp_path, "rb") as audio_file:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=self.config["language"]
                    )

                return transcript.text

            finally:
                # 一時ファイルを削除
                os.unlink(temp_path)

        except Exception as e:
            logger.error(f"OpenAI Whisper transcription failed: {e}")
            raise

    async def get_status(self) -> Dict[str, Any]:
        """STTシステムの状態を取得"""
        return {
            "initialized": self.is_initialized,
            "provider": "local" if self.config["use_local"] else "openai",
            "model": self.config["model"],
            "language": self.config["language"],
            "sample_rate": self.config["sample_rate"]
        }

    async def update_config(self, config: Dict[str, Any]):
        """設定を更新"""
        logger.info(f"Updating STT config: {config}")
        old_config = self.config.copy()
        self.config.update(config)

        # モデルが変更された場合は再初期化
        if (old_config.get("model") != self.config.get("model") or
            old_config.get("use_local") != self.config.get("use_local")):
            logger.info("Model changed, reinitializing...")
            await self.cleanup()
            await self.initialize()

    async def cleanup(self):
        """リソースのクリーンアップ"""
        logger.info("Cleaning up Speech-to-Text...")

        if self.whisper_model:
            del self.whisper_model
            self.whisper_model = None

        self.openai_client = None
        self.is_initialized = False
        logger.info("Speech-to-Text cleanup completed")