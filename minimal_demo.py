#!/usr/bin/env python3
"""
Voice AI Agent - 最小機能デモ

外部依存関係なしで動作する最小限のデモ
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


class MinimalDemo:
    """最小機能デモクラス"""

    def __init__(self):
        self.tools = None
        self.memory = None
        self.context = None

    async def initialize(self):
        """デモシステムの初期化"""
        print("🎭 Voice AI Agent 最小機能デモを開始します...")
        print("=" * 50)

        try:
            # 各コンポーネントの初期化
            self.tools = ToolRegistry()
            self.memory = PersonalMemory()
            self.context = ContextManager()

            print("🔧 ツールシステムを初期化中...")
            await self.tools.initialize()

            print("🧠 メモリシステムを初期化中...")
            await self.memory.initialize()

            print("💬 コンテキストマネージャーを初期化中...")
            await self.context.initialize()

            print("✅ システムの初期化が完了しました")

        except Exception as e:
            print(f"❌ システムの初期化に失敗しました: {e}")
            raise

    async def show_system_status(self):
        """システム状態を表示"""
        try:
            print("\n📊 システム状態:")

            # ツールシステム
            if self.tools:
                tools = self.tools.get_available_tools()
                print(f"   🔧 ツールシステム: {len(tools)}個のツールが利用可能")
                for tool in tools:
                    print(f"      - {tool['name']}: {tool['description']}")

            # メモリシステム
            if self.memory:
                memory_status = await self.memory.get_status()
                print(f"   🧠 メモリシステム: {memory_status.get('storage_type', '不明')}ストレージ")
                print(f"      記憶エントリ数: {memory_status.get('memory_count', 0)}")

            # コンテキストシステム
            if self.context:
                context_status = self.context.get_status()
                print(f"   💬 コンテキスト: {context_status.get('message_count', 0)}メッセージ")

        except Exception as e:
            print(f"⚠️  システム状態の取得に失敗: {e}")

    async def test_tools(self):
        """ツール機能のテスト"""
        print("\n🔧 ツール機能テスト")
        print("-" * 30)

        if not self.tools:
            print("❌ ツールシステムが利用できません")
            return

        # 時刻ツールのテスト
        try:
            print("⏰ 時刻ツールをテスト...")
            result = await self.tools.execute_tool("time", {
                "timezone": "Asia/Tokyo",
                "format": "datetime"
            })
            print(f"   結果: {result}")
        except Exception as e:
            print(f"   エラー: {e}")

        # 計算ツールのテスト
        try:
            print("🧮 計算ツールをテスト...")
            result = await self.tools.execute_tool("calculator", {
                "expression": "2 + 3 * 4"
            })
            print(f"   結果: {result}")
        except Exception as e:
            print(f"   エラー: {e}")

        # 単位変換のテスト
        try:
            print("📏 単位変換をテスト...")
            result = await self.tools.execute_tool("calculator", {
                "unit_conversion": "100 cm to m"
            })
            print(f"   結果: {result}")
        except Exception as e:
            print(f"   エラー: {e}")

    async def test_memory(self):
        """メモリ機能のテスト"""
        print("\n🧠 メモリ機能テスト")
        print("-" * 30)

        if not self.memory:
            print("❌ メモリシステムが利用できません")
            return

        # 会話の保存
        try:
            print("💾 会話を記憶に保存...")
            success = await self.memory.store_interaction(
                "こんにちは、私の名前は田中です",
                "こんにちは田中さん！お会いできて嬉しいです。"
            )
            print(f"   結果: {'✅ 成功' if success else '❌ 失敗'}")
        except Exception as e:
            print(f"   エラー: {e}")

        # 設定の保存
        try:
            print("⚙️ ユーザー設定を保存...")
            success = await self.memory.store_user_preference("name", "田中")
            print(f"   結果: {'✅ 成功' if success else '❌ 失敗'}")
        except Exception as e:
            print(f"   エラー: {e}")

        # 記憶の検索
        try:
            print("🔍 関連記憶を検索...")
            results = await self.memory.search_relevant("名前", limit=2)
            print(f"   結果: {len(results)}件の関連記憶を発見")
            for result in results[:2]:
                print(f"      - {result.get('content', '内容なし')[:50]}...")
        except Exception as e:
            print(f"   エラー: {e}")

    async def interactive_mode(self):
        """インタラクティブモード（テキストベース）"""
        print("\n💬 インタラクティブモード")
        print("簡単なテキスト処理をテストします。'exit'で終了。")
        print("-" * 50)

        while True:
            try:
                user_input = input("\n👤 あなた: ").strip()

                if user_input.lower() in ['exit', '終了', 'quit']:
                    print("👋 インタラクティブモードを終了します。")
                    break

                if not user_input:
                    continue

                # コンテキストに追加
                await self.context.add_user_message(user_input)

                # 簡単な応答生成（ルールベース）
                response = self.generate_simple_response(user_input)

                await self.context.add_assistant_message(response)

                print(f"🤖 エージェント: {response}")

                # メモリに保存
                if self.memory:
                    await self.memory.store_interaction(user_input, response)

            except KeyboardInterrupt:
                print("\n👋 インタラクティブモードを終了します。")
                break
            except Exception as e:
                print(f"❌ エラーが発生しました: {e}")

    def generate_simple_response(self, user_input: str) -> str:
        """簡単なルールベース応答生成"""
        input_lower = user_input.lower()

        # 挨拶
        if any(word in input_lower for word in ['こんにちは', 'おはよう', 'こんばんは', 'はじめまして']):
            return "こんにちは！お元気ですか？何かお手伝いできることはありますか？"

        # 計算
        if '計算' in input_lower or '+' in user_input or '-' in user_input or '*' in user_input or '/' in user_input:
            return f"計算のご要望ですね。計算ツールを使って '{user_input}' を処理することができます。"

        # 時刻
        if any(word in input_lower for word in ['時刻', '時間', '何時', '日付']):
            return "時刻や日付についてのお問い合わせですね。時刻ツールで詳細な情報を提供できます。"

        # 名前
        if '名前' in input_lower:
            if 'は' in user_input and ('です' in user_input or 'だ' in user_input):
                return "お名前を教えていただき、ありがとうございます！記憶しておきますね。"
            else:
                return "お名前についてのお問い合わせですね。何かお聞きしたいことはありますか？"

        # 一般的な応答
        return f"「{user_input}」についてですね。申し訳ありませんが、現在は限定的な機能のデモモードです。より詳細な対応には追加のAPIキー設定が必要です。"

    async def cleanup(self):
        """システムのクリーンアップ"""
        print("\n🧹 システムをクリーンアップ中...")

        cleanup_tasks = []
        if self.tools:
            cleanup_tasks.append(self.tools.cleanup())
        if self.memory:
            cleanup_tasks.append(self.memory.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        print("✅ クリーンアップ完了")


async def main():
    """メイン関数"""
    demo = MinimalDemo()

    try:
        # システム初期化
        await demo.initialize()

        # デモメニュー
        while True:
            print("\n" + "=" * 50)
            print("🎭 Voice AI Agent 最小機能デモメニュー")
            print("=" * 50)
            print("1. システム状態表示")
            print("2. ツール機能テスト")
            print("3. メモリ機能テスト")
            print("4. インタラクティブモード")
            print("0. 終了")
            print("-" * 50)

            try:
                choice = input("選択してください (0-4): ").strip()

                if choice == "1":
                    await demo.show_system_status()
                elif choice == "2":
                    await demo.test_tools()
                elif choice == "3":
                    await demo.test_memory()
                elif choice == "4":
                    await demo.interactive_mode()
                elif choice == "0":
                    print("👋 デモを終了します。")
                    break
                else:
                    print("❌ 無効な選択です。")

            except KeyboardInterrupt:
                print("\n👋 デモを終了します。")
                break

    except Exception as e:
        print(f"❌ デモの実行に失敗しました: {e}")

    finally:
        # クリーンアップ
        await demo.cleanup()


if __name__ == "__main__":
    # ログレベルを調整
    logger.remove()
    logger.add(sys.stderr, level="WARNING")  # 警告レベルのみ表示

    print("🎉 Voice AI Agent 最小機能デモンストレーション")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("💡 このデモは外部APIキーなしで基本機能をテストします")

    # デモ実行
    asyncio.run(main())