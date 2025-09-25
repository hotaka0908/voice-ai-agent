#!/usr/bin/env python3
"""
Speech-to-text debug script - 音声認識バグを特定するテストスクリプト
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv('/Users/funahashihotaka/dev/voiceagent/.env')

# プロジェクトのrootディレクトリをパスに追加
sys.path.append('/Users/funahashihotaka/dev/voiceagent')

from src.audio.speech_to_text import SpeechToText

async def test_stt():
    """STTクラスのテスト"""
    print("🔧 Speech-to-Text Debug Test")

    # ダミーの音声データを作成（WAV形式）
    # WAVヘッダー + 短いダミーデータ
    wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x3f\x00\x00\x80\x7e\x00\x00\x02\x00\x10\x00data\x00\x08\x00\x00'
    dummy_audio_data = wav_header + b'\x00' * 2048  # 短い音声データ

    try:
        # STTインスタンスを作成
        stt = SpeechToText()

        print("📡 Initializing STT...")
        await stt.initialize()

        print(f"✅ STT initialized: {stt.is_initialized}")
        print(f"🔧 Config: {stt.config}")

        print("🎤 Testing with dummy audio data...")
        result = await stt.transcribe(dummy_audio_data)
        print(f"📝 Result: {result}")

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        print("🔍 Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_stt())