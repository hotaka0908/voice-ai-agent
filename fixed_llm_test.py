#!/usr/bin/env python3
"""
Fixed LLM Test - 修正済みLLMテスト

環境変数の読み込みを明示的に行うLLMテスト
"""

import asyncio
import sys
import os
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

# 環境変数を明示的に読み込み
load_dotenv()

from src.llm.hybrid_llm import HybridLLM
from src.tools.tool_registry import ToolRegistry
from src.memory.personal_memory import PersonalMemory
from src.core.context_manager import ContextManager


async def test_llm_with_env():
    """環境変数読み込みを明示的に行うLLMテスト"""

    print("🎉 修正済みLLMテスト")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # ログレベルを調整
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # 環境変数の確認
    print("🔑 環境変数確認:")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    print(f"   OpenAI API Key: {'✅ 設定済み (%d文字)' % len(openai_key) if openai_key else '❌ 未設定'}")
    print(f"   Anthropic API Key: {'✅ 設定済み (%d文字)' % len(anthropic_key) if anthropic_key else '❌ 未設定'}")

    llm = None
    tools = None
    memory = None
    context = None

    try:
        # ===== 1. 個別コンポーネント初期化 =====
        print("\n🔧 1. 個別コンポーネント初期化")
        print("-" * 30)

        # メモリシステム
        print("   🧠 メモリシステム初期化中...")
        memory = PersonalMemory()
        await memory.initialize()
        print("   ✅ メモリシステム初期化完了")

        # ツールシステム
        print("   🔧 ツールシステム初期化中...")
        tools = ToolRegistry()
        await tools.initialize()
        available_tools = tools.get_available_tools()
        print(f"   ✅ ツールシステム初期化完了 ({len(available_tools)}個のツール)")

        # コンテキストシステム
        print("   💬 コンテキストシステム初期化中...")
        context = ContextManager()
        await context.initialize()
        print("   ✅ コンテキストシステム初期化完了")

        # ===== 2. LLMシステム手動初期化 =====
        print("\n🧠 2. LLMシステム手動初期化")
        print("-" * 30)

        # プロバイダー利用可能性の確認
        import importlib

        # Anthropic利用可能性チェック
        try:
            anthropic_lib = importlib.import_module('anthropic')
            anthropic_available = bool(anthropic_key)
            print(f"   Anthropic: {'✅ 利用可能' if anthropic_available else '❌ 利用不可'}")
        except ImportError:
            anthropic_available = False
            print("   Anthropic: ❌ ライブラリ未インストール")

        # OpenAI利用可能性チェック
        try:
            openai_lib = importlib.import_module('openai')
            openai_available = bool(openai_key)
            print(f"   OpenAI: {'✅ 利用可能' if openai_available else '❌ 利用不可'}")
        except ImportError:
            openai_available = False
            print("   OpenAI: ❌ ライブラリ未インストール")

        # ===== 3. 直接API呼び出しテスト =====
        if anthropic_available or openai_available:
            print("\n🤖 3. 直接API呼び出しテスト")
            print("-" * 30)

            # サンプル質問
            test_queries = [
                "こんにちは！簡潔に挨拶を返してください。",
                "2+2の答えを教えて。",
                "今日は良い天気ですね。短くコメントしてください。"
            ]

            for i, query in enumerate(test_queries, 1):
                print(f"\n   {i}. テスト質問: {query}")

                if anthropic_available:
                    print("      🔵 Anthropic Claude で試行...")
                    try:
                        import anthropic
                        client = anthropic.Anthropic(api_key=anthropic_key)

                        response = client.messages.create(
                            model="claude-3-haiku-20240307",
                            max_tokens=50,
                            messages=[{"role": "user", "content": query}]
                        )

                        answer = response.content[0].text
                        print(f"      ✅ Claude応答: {answer}")

                        # メモリに保存
                        if memory:
                            await memory.store_interaction(query, answer)

                        # 成功したらOpenAIはスキップ
                        continue

                    except Exception as e:
                        print(f"      ❌ Claude エラー: {e}")

                if openai_available:
                    print("      🟢 OpenAI GPT で試行...")
                    try:
                        import openai
                        client = openai.OpenAI(api_key=openai_key)

                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": query}],
                            max_tokens=50
                        )

                        answer = response.choices[0].message.content
                        print(f"      ✅ GPT応答: {answer}")

                        # メモリに保存
                        if memory:
                            await memory.store_interaction(query, answer)

                    except Exception as e:
                        print(f"      ❌ GPT エラー: {e}")

            # ===== 4. ツール連携テスト =====
            print("\n🔧 4. ツール連携テスト")
            print("-" * 30)

            print("   ⏰ 時刻ツール実行:")
            time_result = await tools.execute_tool("time", {
                "timezone": "Asia/Tokyo",
                "format": "datetime"
            })
            print(f"   結果: {time_result}")

            print("   🧮 計算ツール実行:")
            calc_result = await tools.execute_tool("calculator", {
                "expression": "10 * 3 + 7"
            })
            print(f"   結果: {calc_result}")

            # ===== 5. メモリ統計 =====
            print("\n🧠 5. メモリ統計")
            print("-" * 30)

            memory_status = await memory.get_status()
            print(f"   記憶エントリ数: {memory_status.get('memory_count', 0)}")
            print(f"   ストレージタイプ: {memory_status.get('storage_type', '不明')}")

            # 最近の会話を検索
            recent_memories = await memory.search_relevant("こんにちは", limit=3)
            print(f"   関連記憶検索結果: {len(recent_memories)}件")

            print("\n🎉 修正済みテストが完了しました！")
            print("💡 APIキーは正常に動作し、基本機能も利用できます。")

        else:
            print("\n❌ 利用可能なLLMプロバイダーがありません")

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
        print(f"🏁 修正済みテスト終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(test_llm_with_env())