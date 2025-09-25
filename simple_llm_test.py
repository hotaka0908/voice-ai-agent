#!/usr/bin/env python3
"""
Simple LLM Test - 直接APIテスト

APIキーが正しく動作するかを直接テスト
"""

import asyncio
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

async def test_openai():
    """OpenAI APIの直接テスト"""
    print("🔍 OpenAI APIテスト")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API key not found")
        return False

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)

        # 簡単なテスト
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, say 'API works' if you can read this."}],
            max_tokens=10
        )

        result = response.choices[0].message.content
        print(f"✅ OpenAI API: {result}")
        return True

    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        return False

async def test_anthropic():
    """Anthropic APIの直接テスト"""
    print("🔍 Anthropic APIテスト")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Anthropic API key not found")
        return False

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        # 簡単なテスト
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello, say 'API works' if you can read this."}]
        )

        result = response.content[0].text
        print(f"✅ Anthropic API: {result}")
        return True

    except Exception as e:
        print(f"❌ Anthropic API error: {e}")
        return False

async def main():
    print("🎯 API キー直接テスト")
    print("=" * 40)

    # APIキーの存在確認
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    print(f"OpenAI API Key: {'✅ 設定済み' if openai_key else '❌ 未設定'}")
    print(f"Anthropic API Key: {'✅ 設定済み' if anthropic_key else '❌ 未設定'}")

    if openai_key:
        print(f"OpenAI Key length: {len(openai_key)}")
        print(f"OpenAI Key prefix: {openai_key[:20]}...")

    if anthropic_key:
        print(f"Anthropic Key length: {len(anthropic_key)}")
        print(f"Anthropic Key prefix: {anthropic_key[:20]}...")

    print("\n🧪 API接続テスト実行中...")

    # APIテスト実行
    openai_success = await test_openai()
    anthropic_success = await test_anthropic()

    print("\n📋 テスト結果:")
    print(f"OpenAI API: {'✅ 成功' if openai_success else '❌ 失敗'}")
    print(f"Anthropic API: {'✅ 成功' if anthropic_success else '❌ 失敗'}")

    if openai_success or anthropic_success:
        print("\n🎉 少なくとも1つのAPIが利用可能です！")
    else:
        print("\n❌ すべてのAPIが利用できません")

if __name__ == "__main__":
    asyncio.run(main())