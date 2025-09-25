#!/usr/bin/env python3
"""
Voice AI Agent - デモンストレーション

システムの主要機能をデモンストレーションするスクリプト
"""

import asyncio
import sys
import os
from datetime import datetime
from loguru import logger

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

from src.core.agent import VoiceAgent
from src.llm.hybrid_llm import HybridLLM
from src.tools.tool_registry import ToolRegistry
from src.memory.personal_memory import PersonalMemory


class VoiceAgentDemo:
    """音声AIエージェントのデモクラス"""

    def __init__(self):
        self.agent = None
        self.demo_scenarios = [
            {
                "name": "基本的な会話",
                "inputs": [
                    "こんにちは",
                    "今日の天気はどうですか？",
                    "ありがとうございます"
                ]
            },
            {
                "name": "計算機能",
                "inputs": [
                    "2 + 3を計算して",
                    "100センチをメートルに変換して",
                    "32度の華氏を摂氏に変換して"
                ]
            },
            {
                "name": "時刻・日付",
                "inputs": [
                    "今の時刻を教えて",
                    "今日の日付は？",
                    "東京とニューヨークの時差を教えて"
                ]
            },
            {
                "name": "メモリ機能",
                "inputs": [
                    "私の名前を田中と覚えておいて",
                    "私の好きな食べ物はラーメンです",
                    "私の名前は何ですか？"
                ]
            },
            {
                "name": "スマートホーム制御",
                "inputs": [
                    "利用可能なデバイスを教えて",
                    "リビングの照明をつけて",
                    "エアコンの温度を25度にして"
                ]
            }
        ]

    async def initialize(self):
        """デモシステムの初期化"""
        print("🎭 Voice AI Agent デモを開始します...")
        print("=" * 50)

        try:
            # VoiceAgentの初期化
            self.agent = VoiceAgent()
            await self.agent.initialize()

            print("✅ システムの初期化が完了しました")

            # システム状態の表示
            await self.show_system_status()

        except Exception as e:
            print(f"❌ システムの初期化に失敗しました: {e}")
            raise

    async def show_system_status(self):
        """システム状態を表示"""
        try:
            status = await self.agent.get_status()

            print("\n📊 システム状態:")
            print(f"   メインシステム: {'✅ 準備完了' if status.get('status') == 'ready' else '❌ 未準備'}")

            components = status.get('components', {})
            for component_name, component_status in components.items():
                if isinstance(component_status, dict):
                    initialized = component_status.get('initialized', False)
                    print(f"   {component_name}: {'✅ 初期化済み' if initialized else '❌ 未初期化'}")

        except Exception as e:
            print(f"⚠️  システム状態の取得に失敗: {e}")

    async def run_interactive_demo(self):
        """インタラクティブデモの実行"""
        print("\n🎤 インタラクティブモード")
        print("テキストで質問を入力してください。終了するには 'exit' と入力してください。")
        print("-" * 50)

        while True:
            try:
                user_input = input("\n👤 あなた: ").strip()

                if user_input.lower() in ['exit', '終了', 'quit']:
                    print("👋 デモを終了します。")
                    break

                if not user_input:
                    continue

                print("🤖 処理中...")

                # エージェントでテキストを処理
                response = await self.agent.process_text(user_input)

                print(f"🤖 エージェント: {response.get('text', '応答を生成できませんでした。')}")

                # ツール使用があれば表示
                if response.get('tool_results'):
                    print("🔧 使用したツール:")
                    for tool_result in response.get('tool_results', []):
                        print(f"   - {tool_result}")

            except KeyboardInterrupt:
                print("\n\n👋 デモを終了します。")
                break
            except Exception as e:
                print(f"❌ エラーが発生しました: {e}")

    async def run_scenario_demo(self):
        """シナリオベースのデモ実行"""
        print("\n🎬 シナリオベースデモ")
        print("=" * 50)

        for i, scenario in enumerate(self.demo_scenarios, 1):
            print(f"\n📋 シナリオ {i}: {scenario['name']}")
            print("-" * 30)

            for j, user_input in enumerate(scenario['inputs'], 1):
                try:
                    print(f"\n{j}. 👤 ユーザー: {user_input}")
                    print("   🤖 処理中...")

                    # エージェントでテキストを処理
                    response = await self.agent.process_text(user_input)

                    agent_response = response.get('text', '応答を生成できませんでした。')
                    print(f"   🤖 エージェント: {agent_response}")

                    # ツール結果があれば表示
                    if response.get('tool_results'):
                        print("   🔧 ツール実行結果:")
                        for tool_result in response.get('tool_results', []):
                            print(f"      - {tool_result}")

                    # 少し待機
                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"   ❌ エラー: {e}")

            # シナリオ間の待機
            await asyncio.sleep(2)

    async def run_component_tests(self):
        """個別コンポーネントのテスト"""
        print("\n🧪 コンポーネント個別テスト")
        print("=" * 50)

        # LLMシステムテスト
        await self.test_llm_system()

        # ツールシステムテスト
        await self.test_tool_system()

        # メモリシステムテスト
        await self.test_memory_system()

    async def test_llm_system(self):
        """LLMシステムのテスト"""
        print("\n🧠 LLMシステムテスト")
        try:
            if self.agent.llm and self.agent.llm.is_initialized:
                status = await self.agent.llm.get_status()
                print("✅ LLMシステム動作確認")
                print(f"   プライマリプロバイダー: {status.get('primary_provider', '不明')}")
                print(f"   フォールバックプロバイダー: {status.get('fallback_provider', '不明')}")

                # 利用可能なプロバイダーを表示
                providers = status.get('providers', {})
                for name, provider_status in providers.items():
                    available = provider_status.get('available', False)
                    print(f"   {name}: {'✅ 利用可能' if available else '❌ 利用不可'}")
            else:
                print("❌ LLMシステムが初期化されていません")
        except Exception as e:
            print(f"❌ LLMシステムテストエラー: {e}")

    async def test_tool_system(self):
        """ツールシステムのテスト"""
        print("\n🔧 ツールシステムテスト")
        try:
            if self.agent.tools and self.agent.tools.is_initialized:
                tools = self.agent.tools.get_available_tools()
                print(f"✅ {len(tools)}個のツールが利用可能")

                for tool in tools[:5]:  # 最初の5個を表示
                    print(f"   - {tool['name']}: {tool['description']}")

                if len(tools) > 5:
                    print(f"   ... 他{len(tools) - 5}個のツール")

                # 簡単なツールテスト
                try:
                    result = await self.agent.tools.execute_tool("time", {
                        "timezone": "Asia/Tokyo",
                        "format": "time"
                    })
                    print(f"   時刻ツールテスト: {result}")
                except Exception as e:
                    print(f"   時刻ツールテストエラー: {e}")

            else:
                print("❌ ツールシステムが初期化されていません")
        except Exception as e:
            print(f"❌ ツールシステムテストエラー: {e}")

    async def test_memory_system(self):
        """メモリシステムのテスト"""
        print("\n🧠 メモリシステムテスト")
        try:
            if self.agent.memory and self.agent.memory.is_initialized:
                status = await self.agent.memory.get_status()
                print("✅ メモリシステム動作確認")
                print(f"   ストレージタイプ: {status.get('storage_type', '不明')}")
                print(f"   記憶エントリ数: {status.get('memory_count', 0)}")

                # 簡単な記憶テスト
                success = await self.agent.memory.store_interaction(
                    "デモテスト",
                    "これはデモ用のテストです"
                )
                print(f"   記憶テスト: {'✅ 成功' if success else '❌ 失敗'}")

            else:
                print("❌ メモリシステムが初期化されていません")
        except Exception as e:
            print(f"❌ メモリシステムテストエラー: {e}")

    async def cleanup(self):
        """デモシステムのクリーンアップ"""
        print("\n🧹 システムをクリーンアップ中...")

        if self.agent:
            await self.agent.cleanup()

        print("✅ クリーンアップ完了")


async def main():
    """メイン関数"""
    demo = VoiceAgentDemo()

    try:
        # システム初期化
        await demo.initialize()

        # デモメニューの表示
        while True:
            print("\n" + "=" * 50)
            print("🎭 Voice AI Agent デモメニュー")
            print("=" * 50)
            print("1. インタラクティブモード（テキスト入力）")
            print("2. シナリオベースデモ")
            print("3. コンポーネント個別テスト")
            print("4. システム状態表示")
            print("0. 終了")
            print("-" * 50)

            try:
                choice = input("選択してください (0-4): ").strip()

                if choice == "1":
                    await demo.run_interactive_demo()
                elif choice == "2":
                    await demo.run_scenario_demo()
                elif choice == "3":
                    await demo.run_component_tests()
                elif choice == "4":
                    await demo.show_system_status()
                elif choice == "0":
                    print("👋 デモを終了します。")
                    break
                else:
                    print("❌ 無効な選択です。")

            except KeyboardInterrupt:
                print("\n\n👋 デモを終了します。")
                break

    except Exception as e:
        print(f"❌ デモの実行に失敗しました: {e}")

    finally:
        # クリーンアップ
        await demo.cleanup()


if __name__ == "__main__":
    # ログレベルを調整
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    print("🎉 Voice AI Agent デモンストレーション")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # デモ実行
    asyncio.run(main())