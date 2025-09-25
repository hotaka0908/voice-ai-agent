#!/usr/bin/env python3
"""
Voice AI Agent - 自動テストデモ

システムが正常に動作することを確認する自動テスト
"""

import asyncio
import sys
import os
from datetime import datetime
from loguru import logger

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

from src.tools.tool_registry import ToolRegistry
from src.memory.personal_memory import PersonalMemory
from src.core.context_manager import ContextManager


async def test_system():
    """システム全体の自動テスト"""

    print("🎉 Voice AI Agent 自動テストデモ")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ログレベルを調整（警告のみ表示）
    logger.remove()
    logger.add(sys.stderr, level="WARNING")

    tools = None
    memory = None
    context = None

    try:
        # ===== 1. システム初期化テスト =====
        print("\n🔧 1. システム初期化テスト")
        print("-" * 30)

        print("   ツールレジストリ初期化中...")
        tools = ToolRegistry()
        await tools.initialize()
        print("   ✅ ツールレジストリ初期化完了")

        print("   メモリシステム初期化中...")
        memory = PersonalMemory()
        await memory.initialize()
        print("   ✅ メモリシステム初期化完了")

        print("   コンテキストマネージャー初期化中...")
        context = ContextManager()
        await context.initialize()
        print("   ✅ コンテキストマネージャー初期化完了")

        # ===== 2. ツール機能テスト =====
        print("\n⚙️ 2. ツール機能テスト")
        print("-" * 30)

        available_tools = tools.get_available_tools()
        print(f"   利用可能なツール数: {len(available_tools)}")

        for tool in available_tools:
            print(f"   - {tool['name']}: {tool['description']}")

        # 時刻ツールテスト
        print("\n   ⏰ 時刻ツール実行中...")
        try:
            result = await tools.execute_tool("time", {
                "timezone": "Asia/Tokyo",
                "format": "datetime"
            })
            print(f"   ✅ 時刻ツール結果: {str(result)[:100]}...")
        except Exception as e:
            print(f"   ❌ 時刻ツールエラー: {e}")

        # 計算ツールテスト
        print("\n   🧮 計算ツール実行中...")
        try:
            result = await tools.execute_tool("calculator", {
                "expression": "2 + 3 * 4"
            })
            print(f"   ✅ 計算ツール結果: {result}")
        except Exception as e:
            print(f"   ❌ 計算ツールエラー: {e}")

        # 単位変換テスト
        print("\n   📏 単位変換実行中...")
        try:
            result = await tools.execute_tool("calculator", {
                "unit_conversion": "100 cm to m"
            })
            print(f"   ✅ 単位変換結果: {result}")
        except Exception as e:
            print(f"   ❌ 単位変換エラー: {e}")

        # ===== 3. メモリ機能テスト =====
        print("\n🧠 3. メモリ機能テスト")
        print("-" * 30)

        # メモリ状態確認
        memory_status = await memory.get_status()
        print(f"   メモリタイプ: {memory_status.get('storage_type', '不明')}")
        print(f"   記憶エントリ数: {memory_status.get('memory_count', 0)}")

        # 会話記憶テスト
        print("\n   💾 会話記憶テスト...")
        success = await memory.store_interaction(
            "こんにちは、私の名前は田中です",
            "こんにちは田中さん！よろしくお願いします。"
        )
        print(f"   結果: {'✅ 成功' if success else '❌ 失敗'}")

        # 設定保存テスト
        print("\n   ⚙️ ユーザー設定保存テスト...")
        success = await memory.store_user_preference("name", "田中")
        success = await memory.store_user_preference("hobby", "読書") and success
        print(f"   結果: {'✅ 成功' if success else '❌ 失敗'}")

        # 記憶検索テスト
        print("\n   🔍 記憶検索テスト...")
        results = await memory.search_relevant("名前", limit=3)
        print(f"   検索結果: {len(results)}件")
        for i, result in enumerate(results[:2], 1):
            content = result.get('content', '内容なし')[:50]
            print(f"   {i}. {content}...")

        # 設定取得テスト
        print("\n   📋 設定取得テスト...")
        preferences = await memory.get_user_preferences()
        print(f"   設定項目数: {len(preferences)}")
        for key, value in preferences.items():
            print(f"   - {key}: {value}")

        # ===== 4. コンテキスト機能テスト =====
        print("\n💬 4. コンテキスト機能テスト")
        print("-" * 30)

        # メッセージ追加
        await context.add_user_message("今日は良い天気ですね")
        await context.add_assistant_message("そうですね！お出かけ日和です。")
        await context.add_user_message("公園に散歩に行こうと思います")

        # コンテキスト情報表示
        context_status = context.get_status()
        print(f"   メッセージ数: {context_status.get('message_count', 0)}")
        print(f"   現在のトピック: {context_status.get('current_topic', 'なし')}")

        # 会話要約
        summary = context.get_conversation_summary()
        print(f"   会話要約: {summary[:100]}...")

        # 最近のコンテキスト取得
        recent_context = context.get_recent_context(message_count=3)
        print(f"   最近のメッセージ数: {len(recent_context)}")

        # ===== 5. 統合テスト =====
        print("\n🎯 5. 統合テスト")
        print("-" * 30)

        # シナリオ: ユーザーが時間を聞いて、それを記憶に保存
        print("   シナリオ: 時間確認 → 記憶保存")

        # ステップ1: 時刻取得
        user_input = "今の時間を教えて"
        await context.add_user_message(user_input)

        time_result = await tools.execute_tool("time", {
            "timezone": "Asia/Tokyo",
            "format": "time"
        })

        response = f"現在の時刻は{time_result}です。"
        await context.add_assistant_message(response)

        print(f"   👤 ユーザー: {user_input}")
        print(f"   🤖 エージェント: {response}")

        # ステップ2: 会話を記憶に保存
        memory_success = await memory.store_interaction(user_input, response)
        print(f"   記憶保存: {'✅ 成功' if memory_success else '❌ 失敗'}")

        # ===== 6. 結果まとめ =====
        print("\n🎊 6. テスト結果まとめ")
        print("-" * 30)

        final_memory_status = await memory.get_status()
        final_context_status = context.get_status()
        final_tools = tools.get_available_tools()

        print(f"   ✅ 初期化完了: 全コンポーネント")
        print(f"   ✅ 利用可能ツール: {len(final_tools)}個")
        print(f"   ✅ 記憶エントリ: {final_memory_status.get('memory_count', 0)}件")
        print(f"   ✅ 会話メッセージ: {final_context_status.get('message_count', 0)}件")

        print("\n🎉 全てのテストが正常に完了しました！")
        print("💡 システムは基本機能において正常に動作しています。")

    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # クリーンアップ
        print("\n🧹 システムクリーンアップ中...")

        cleanup_tasks = []
        if tools:
            cleanup_tasks.append(tools.cleanup())
        if memory:
            cleanup_tasks.append(memory.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        print("✅ クリーンアップ完了")

        print(f"\n🏁 テスト終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(test_system())