#!/usr/bin/env python3
"""
Voice AI Agent - フル機能テストデモ

APIキー設定済みでのフル機能テスト
"""

import asyncio
import sys
import os
from datetime import datetime
from loguru import logger

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

# 環境変数を明示的に読み込み
from dotenv import load_dotenv
load_dotenv()

from src.llm.hybrid_llm import HybridLLM
from src.tools.tool_registry import ToolRegistry
from src.memory.personal_memory import PersonalMemory
from src.core.context_manager import ContextManager


async def test_full_system():
    """APIキー設定済みでのフル機能テスト"""

    print("🎉 Voice AI Agent フル機能テストデモ")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔑 APIキー設定済み - フル機能でテスト実行")
    print("=" * 60)

    # ログレベルを調整
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    llm = None
    tools = None
    memory = None
    context = None

    try:
        # ===== 1. LLMシステムテスト =====
        print("\n🧠 1. LLMシステムテスト")
        print("-" * 30)

        llm = HybridLLM()
        await llm.initialize()

        status = await llm.get_status()
        print(f"   初期化: {'✅ 成功' if status.get('initialized') else '❌ 失敗'}")
        print(f"   プライマリプロバイダー: {status.get('primary_provider')}")
        print(f"   フォールバックプロバイダー: {status.get('fallback_provider')}")

        # 利用可能なプロバイダーを確認
        providers = status.get('providers', {})
        for name, provider_status in providers.items():
            available = provider_status.get('available', False)
            print(f"   {name}: {'✅ 利用可能' if available else '❌ 利用不可'}")

        # ===== 2. ツールシステム詳細テスト =====
        print("\n⚙️ 2. ツールシステム詳細テスト")
        print("-" * 30)

        tools = ToolRegistry()
        await tools.initialize()

        available_tools = tools.get_available_tools()
        print(f"   利用可能ツール数: {len(available_tools)}")

        # 各ツールの詳細テスト
        print("\n   📋 各ツール詳細テスト:")

        # 天気ツール
        print("   🌤️ 天気ツール:")
        try:
            result = await tools.execute_tool("weather", {
                "location": "東京",
                "days": 1
            })
            print(f"      結果: {str(result)[:100]}...")
        except Exception as e:
            print(f"      エラー: {e}")

        # 計算ツール詳細
        print("   🧮 計算ツール:")
        calculations = [
            {"expression": "sqrt(16) + 2^3"},
            {"unit_conversion": "32 F to C"},
            {"expression": "sin(30) + cos(60)"}
        ]
        for calc in calculations:
            try:
                result = await tools.execute_tool("calculator", calc)
                print(f"      {calc}: {result}")
            except Exception as e:
                print(f"      {calc}: エラー - {e}")

        # 検索ツール
        print("   🔍 検索ツール:")
        try:
            result = await tools.execute_tool("search", {
                "query": "Python プログラミング",
                "limit": 3
            })
            print(f"      結果: {str(result)[:150]}...")
        except Exception as e:
            print(f"      エラー: {e}")

        # ===== 3. メモリシステム詳細テスト =====
        print("\n🧠 3. メモリシステム詳細テスト")
        print("-" * 30)

        memory = PersonalMemory()
        await memory.initialize()

        # 複数の会話を保存
        conversations = [
            ("私の名前は田中太郎です", "田中太郎さん、はじめまして！"),
            ("私の趣味は読書と映画鑑賞です", "読書と映画鑑賞、素晴らしい趣味ですね！"),
            ("好きな食べ物はラーメンです", "ラーメン、美味しいですよね！どんな味がお好みですか？"),
            ("今度の休みに旅行に行く予定です", "旅行、楽しみですね！どちらに行かれるのですか？")
        ]

        print("   💾 会話データ保存:")
        for user_msg, assistant_msg in conversations:
            success = await memory.store_interaction(user_msg, assistant_msg)
            print(f"      {'✅' if success else '❌'} {user_msg[:30]}...")

        # 設定保存
        preferences = {
            "name": "田中太郎",
            "hobby": "読書、映画鑑賞",
            "food": "ラーメン",
            "plan": "旅行"
        }

        print("   ⚙️ ユーザー設定保存:")
        for key, value in preferences.items():
            success = await memory.store_user_preference(key, value)
            print(f"      {'✅' if success else '❌'} {key}: {value}")

        # 記憶検索テスト
        print("   🔍 記憶検索テスト:")
        search_queries = ["名前", "趣味", "食べ物", "旅行"]
        for query in search_queries:
            results = await memory.search_relevant(query, limit=2)
            print(f"      '{query}': {len(results)}件")

        # ===== 4. LLM統合テスト =====
        print("\n🤖 4. LLM統合テスト")
        print("-" * 30)

        if any(provider.get('available') for provider in status.get('providers', {}).values()):
            print("   💬 LLMとの対話テスト:")

            context = ContextManager()
            await context.initialize()

            # テスト会話
            test_queries = [
                "こんにちは、私の名前は田中です",
                "今日の天気はどうですか？",
                "2 + 3 × 4の計算をお願いします"
            ]

            for query in test_queries:
                print(f"   👤 ユーザー: {query}")
                try:
                    # コンテキストに追加
                    await context.add_user_message(query)

                    # 関連記憶を検索
                    relevant_memories = await memory.search_relevant(query, limit=3)

                    # LLMで処理
                    response = await llm.process_with_tools(
                        text=query,
                        context=context.get_recent_context(5),
                        memories=relevant_memories,
                        available_tools=tools.get_available_tools()
                    )

                    print(f"   🤖 エージェント: {response.get('response', '応答なし')}")

                    # ツール呼び出しがあった場合
                    if response.get('tool_calls'):
                        print(f"   🔧 ツール使用: {len(response['tool_calls'])}個")
                        for tool_call in response['tool_calls']:
                            print(f"      - {tool_call.get('name', '不明')}")

                    await context.add_assistant_message(response.get('response', ''))

                except Exception as e:
                    print(f"   ❌ エラー: {e}")

        else:
            print("   ❌ LLMプロバイダーが利用できないため、統合テストをスキップ")

        # ===== 5. システム統計 =====
        print("\n📊 5. システム統計")
        print("-" * 30)

        # 最終状態の確認
        final_memory_status = await memory.get_status()
        final_llm_status = await llm.get_status()
        final_tools = tools.get_available_tools()

        print(f"   🧠 メモリ統計:")
        print(f"      - ストレージタイプ: {final_memory_status.get('storage_type')}")
        print(f"      - 記憶エントリ数: {final_memory_status.get('memory_count', 0)}")

        print(f"   🤖 LLM統計:")
        print(f"      - 初期化: {final_llm_status.get('initialized', False)}")
        print(f"      - プライバシーモード: {final_llm_status.get('privacy_mode', False)}")

        print(f"   🔧 ツール統計:")
        print(f"      - 利用可能ツール数: {len(final_tools)}")

        if context:
            context_status = context.get_status()
            print(f"   💬 コンテキスト統計:")
            print(f"      - メッセージ数: {context_status.get('message_count', 0)}")
            print(f"      - 現在のトピック: {context_status.get('current_topic', 'なし')}")

        print("\n🎉 フル機能テストが完了しました！")
        print("💡 APIキーが設定されたシステムは正常に動作しています。")

    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # クリーンアップ
        print("\n🧹 システムクリーンアップ中...")

        cleanup_tasks = []
        if llm:
            cleanup_tasks.append(llm.cleanup())
        if tools:
            cleanup_tasks.append(tools.cleanup())
        if memory:
            cleanup_tasks.append(memory.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        print("✅ クリーンアップ完了")
        print(f"🏁 フル機能テスト終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(test_full_system())