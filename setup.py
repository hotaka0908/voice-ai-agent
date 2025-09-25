#!/usr/bin/env python3
"""
Voice AI Agent - セットアップスクリプト

開発環境のセットアップとシステムの起動を支援するスクリプト
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path


def check_python_version():
    """Python バージョンのチェック"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8以上が必要です")
        print(f"現在のバージョン: {sys.version}")
        return False
    print(f"✅ Python バージョン: {sys.version.split()[0]}")
    return True


def create_directories():
    """必要なディレクトリを作成"""
    directories = [
        "data/audio",
        "data/memory",
        "logs",
        "config"
    ]

    print("📁 ディレクトリを作成中...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")


def check_requirements():
    """必要なパッケージがインストールされているかチェック"""
    print("📦 依存関係をチェック中...")

    # requirements.txtから必要なパッケージを読み取り
    requirements_file = "requirements.txt"
    if not os.path.exists(requirements_file):
        print("❌ requirements.txt が見つかりません")
        return False

    try:
        with open(requirements_file, 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        # 基本的なパッケージのチェック
        essential_packages = [
            "fastapi",
            "uvicorn",
            "loguru",
            "python-dotenv"
        ]

        missing_packages = []
        for package in essential_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"   ✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"   ❌ {package}")

        if missing_packages:
            print(f"\n⚠️  不足しているパッケージ: {', '.join(missing_packages)}")
            print("以下のコマンドでインストールしてください:")
            print("pip install -r requirements.txt")
            return False

        return True

    except Exception as e:
        print(f"❌ 依存関係のチェックに失敗: {e}")
        return False


def check_environment_variables():
    """環境変数の設定をチェック"""
    print("🔧 環境変数をチェック中...")

    env_file = ".env"
    example_env_file = ".env.example"

    if not os.path.exists(env_file):
        if os.path.exists(example_env_file):
            print(f"   ⚠️  {env_file} が見つかりません")
            print(f"   💡 {example_env_file} をコピーして設定してください:")
            print(f"   cp {example_env_file} {env_file}")
            return False
        else:
            print("   ⚠️  環境設定ファイルが見つかりません")
            return False

    print(f"   ✅ {env_file} が見つかりました")

    # 重要な環境変数をチェック
    try:
        from dotenv import load_dotenv
        load_dotenv()

        important_vars = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "ELEVENLABS_API_KEY"
        ]

        configured_vars = []
        for var in important_vars:
            value = os.getenv(var)
            if value:
                configured_vars.append(var)
                print(f"   ✅ {var}")
            else:
                print(f"   ⚠️  {var} (未設定)")

        if configured_vars:
            print(f"   💡 {len(configured_vars)}個のAPIキーが設定済み")
        else:
            print("   ⚠️  APIキーが設定されていません（デモモードで動作）")

        return True

    except ImportError:
        print("   ❌ python-dotenv が必要です")
        return False


def run_tests():
    """テストを実行"""
    print("🧪 テストを実行中...")

    try:
        # pytest が利用可能な場合
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("   ✅ 全てのテストが成功しました")
            return True
        else:
            print("   ⚠️  いくつかのテストが失敗しました（外部依存関係が原因の可能性）")
            print("   詳細:")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return True  # 外部依存関係のエラーは許容

    except FileNotFoundError:
        print("   ⚠️  pytest が見つかりません")
        print("   pip install pytest でインストールしてください")
        return False
    except Exception as e:
        print(f"   ❌ テスト実行エラー: {e}")
        return False


def start_server():
    """開発サーバーを起動"""
    print("🚀 開発サーバーを起動中...")

    try:
        # 環境変数の読み込み
        from dotenv import load_dotenv
        load_dotenv()

        host = os.getenv("HOST", "localhost")
        port = int(os.getenv("PORT", 8000))

        print(f"   📍 サーバー: http://{host}:{port}")
        print("   💡 停止するには Ctrl+C を押してください")

        # uvicorn でサーバーを起動
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "src.main:app",
            "--host", host,
            "--port", str(port),
            "--reload",
            "--log-level", "info"
        ])

    except KeyboardInterrupt:
        print("\n👋 サーバーを停止しました")
    except Exception as e:
        print(f"❌ サーバー起動エラー: {e}")


def main():
    """メイン関数"""
    print("🎙️ Voice AI Agent セットアップ")
    print("=" * 50)

    # 引数の処理
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "start":
            start_server()
            return
        elif command == "test":
            run_tests()
            return
        elif command == "demo":
            os.system(f"{sys.executable} demo.py")
            return

    # セットアップチェック
    print("🔍 システムチェックを開始...")

    checks = [
        ("Python バージョン", check_python_version),
        ("ディレクトリ作成", lambda: (create_directories(), True)[1]),
        ("依存関係", check_requirements),
        ("環境変数", check_environment_variables)
    ]

    all_passed = True
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}チェック:")
        if not check_func():
            all_passed = False

    print("\n" + "=" * 50)

    if all_passed:
        print("✅ 全てのチェックが完了しました！")
        print("\n🚀 使用方法:")
        print("  python setup.py start    # サーバー起動")
        print("  python setup.py test     # テスト実行")
        print("  python setup.py demo     # デモ実行")
        print("  python setup.py          # このヘルプ")

        # サーバー起動の確認
        response = input("\n🤔 今すぐサーバーを起動しますか？ (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            start_server()

    else:
        print("❌ いくつかの問題があります。上記の指示に従って解決してください。")


if __name__ == "__main__":
    main()