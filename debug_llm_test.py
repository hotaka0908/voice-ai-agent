#!/usr/bin/env python3
"""
Debug LLM Test - LLM初期化問題のデバッグ
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 環境変数を最初に読み込み
load_dotenv()

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

async def debug_llm():
    print("🔍 LLM初期化デバッグテスト")
    print("=" * 40)

    # 環境変数確認
    print("🔑 環境変数確認:")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    print(f"   OpenAI API Key: {'✅ あり' if openai_key else '❌ なし'}")
    print(f"   Anthropic API Key: {'✅ あり' if anthropic_key else '❌ なし'}")

    # パッケージ確認
    print("\n📦 パッケージ確認:")
    try:
        import openai
        print("   OpenAI: ✅ インストール済み")
    except ImportError:
        print("   OpenAI: ❌ インストールなし")

    try:
        import anthropic
        print("   Anthropic: ✅ インストール済み")
    except ImportError:
        print("   Anthropic: ❌ インストールなし")

    try:
        import ollama
        print("   Ollama: ✅ インストール済み")
    except ImportError:
        print("   Ollama: ❌ インストールなし")

    # HybridLLM初期化テスト
    print("\n🧠 HybridLLM初期化テスト:")
    try:
        from src.llm.hybrid_llm import HybridLLM
        llm = HybridLLM()

        print("   HybridLLM インスタンス作成: ✅")

        # 初期化実行
        await llm.initialize()
        print("   初期化: ✅ 成功")

        # ステータス確認
        status = await llm.get_status()
        print(f"   プライマリプロバイダー: {status.get('primary_provider')}")
        print(f"   利用可能プロバイダー: {list(status.get('providers', {}).keys())}")

        # 利用可能なプロバイダーの詳細
        providers = status.get('providers', {})
        for name, provider_status in providers.items():
            available = provider_status.get('available', False)
            print(f"   {name}: {'✅' if available else '❌'}")

        # 簡単なテスト
        if any(p.get('available') for p in providers.values()):
            print("\n💬 簡単なテスト:")
            response = await llm.generate_response("Hello, say 'test successful' if you can read this.")
            print(f"   応答: {response}")

        await llm.cleanup()

    except Exception as e:
        print(f"   エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_llm())