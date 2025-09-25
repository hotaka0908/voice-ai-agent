#!/usr/bin/env python3
"""
WebSocket Chat Test - WebSocket経由でチャット機能をテスト

WebUIのチャット機能をテストするためのスクリプト
"""

import asyncio
import json
import websockets
import sys

async def test_chat_websocket():
    """WebSocketチャット機能のテスト"""
    print("🔗 WebSocket Chat Test")
    print("=" * 40)

    uri = "ws://localhost:8000/ws/chat"

    try:
        print(f"接続中: {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket接続成功")

            # テストメッセージ
            test_messages = [
                {"type": "message", "message": "こんにちは！テスト中です。"},
                {"type": "message", "message": "今何時ですか？"},
                {"type": "message", "message": "2 + 3 × 4の計算をお願いします"}
            ]

            for i, msg in enumerate(test_messages, 1):
                print(f"\n📤 送信 {i}: {msg['message']}")

                # メッセージ送信
                await websocket.send(json.dumps(msg))

                # 応答受信（タイムアウト付き）
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=30.0
                    )

                    response_data = json.loads(response)
                    print(f"📥 応答 {i}: {response_data.get('response', response_data)}")

                except asyncio.TimeoutError:
                    print(f"⏰ タイムアウト: 応答がありませんでした")
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析エラー: {e}")
                    print(f"生データ: {response}")

    except websockets.exceptions.ConnectionRefused:
        print("❌ 接続拒否: サーバーが動作していません")
        print("   http://localhost:8000 でサーバーが起動していることを確認してください")
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("WebSocket Chat機能のテスト開始")
    print("サーバーが http://localhost:8000 で動作している必要があります")

    # イベントループを実行
    try:
        asyncio.run(test_chat_websocket())
    except KeyboardInterrupt:
        print("\n\n⌨️ テスト中断")

    print("\n🏁 テスト終了")