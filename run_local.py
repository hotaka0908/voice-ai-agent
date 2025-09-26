#!/usr/bin/env python3
"""
ローカル実行用スクリプト
Voice AI Agentをローカル環境で簡単に起動する
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """必要なファイルと環境をチェック"""
    # .envファイルの確認
    if not os.path.exists('.env'):
        print("⚠️  .envファイルが見つかりません")
        print("   .env.example をコピーして .env を作成し、APIキーを設定してください")
        return False

    # 仮想環境の確認
    if not os.path.exists('venv'):
        print("⚠️  仮想環境が見つかりません")
        print("   python3 -m venv venv で仮想環境を作成してください")
        return False

    return True

def install_dependencies():
    """依存関係をインストール"""
    print("📦 依存関係をインストール中...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        return True
    except subprocess.CalledProcessError:
        print("❌ 依存関係のインストールに失敗しました")
        return False

def start_server():
    """サーバーを起動"""
    print("🚀 Voice AI Agent を起動中...")
    print("   http://localhost:8000 でアクセスできます")
    print("   停止するには Ctrl+C を押してください")

    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "src.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 サーバーを停止しました")
    except subprocess.CalledProcessError as e:
        print(f"❌ サーバーの起動に失敗しました: {e}")

def main():
    """メイン処理"""
    print("🎤 Voice AI Agent - ローカル起動")
    print("=" * 40)

    # 要件チェック
    if not check_requirements():
        sys.exit(1)

    # 依存関係インストール
    if not install_dependencies():
        sys.exit(1)

    # サーバー起動
    start_server()

if __name__ == "__main__":
    main()