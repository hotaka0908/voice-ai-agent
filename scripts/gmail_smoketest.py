#!/usr/bin/env python3
"""
Gmail Smoke Test

GmailTool の認証と基本操作（一覧/読取/送信/下書き）をローカルで検証するスクリプト。

前提:
  - data/gmail_credentials.json が存在する（Google Cloud Consoleで取得したOAuthクライアント）
  - 初回実行時にブラウザで認証フローが開く

使い方:
  python scripts/gmail_smoketest.py list --max 3
  python scripts/gmail_smoketest.py read --id <message_id>
  python scripts/gmail_smoketest.py send --to someone@example.com --subject テスト --body 本文
  python scripts/gmail_smoketest.py compose --to someone@example.com --subject テスト --body 本文
"""

import argparse
import asyncio
import os
import sys
from typing import Dict, Any

# プロジェクトルートをパスに追加
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from src.tools.gmail_tool import GmailTool  # noqa: E402


async def run_action(args: argparse.Namespace):
    tool = GmailTool()

    # 事前チェック
    creds_path = tool.credentials_file
    token_path = tool.token_file
    print(f"Credentials: {creds_path}")
    print(f"Token file:  {token_path}")

    if not os.path.exists(creds_path):
        print("\n[!] data/gmail_credentials.json が見つかりません。")
        print("    Google Cloud ConsoleからOAuth2クライアントJSONをダウンロードして配置してください。")
        sys.exit(1)

    # 初期化（認証は最初のexecute時に実施）
    ok = await tool.initialize()
    if not ok:
        print("[!] GmailTool初期化に失敗しました。依存パッケージを確認してください。")
        sys.exit(1)

    params: Dict[str, Any] = {}
    if args.command == "list":
        params = {"action": "list", "max_results": args.max, "query": args.query or ""}
    elif args.command == "read":
        params = {"action": "read", "message_id": args.id}
    elif args.command == "send":
        params = {"action": "send", "to": args.to, "subject": args.subject, "body": args.body}
    elif args.command == "compose":
        params = {"action": "compose", "to": args.to, "subject": args.subject, "body": args.body}
    elif args.command == "reply":
        params = {"action": "reply", "message_id": args.id, "body": args.body, "reply_quote": not args.no_quote}
    else:
        print("Unknown command")
        sys.exit(2)

    print(f"\nExecuting: {params}")
    result = await tool.execute(params)
    print("\n=== Result ===")
    if result.success:
        print(result.result)
    else:
        print(f"Error: {result.error}")


def main():
    parser = argparse.ArgumentParser(description="Gmail tool smoke test")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List messages")
    p_list.add_argument("--max", type=int, default=5, help="max results")
    p_list.add_argument("--query", type=str, default="", help="Gmail search query")

    p_read = sub.add_parser("read", help="Read a message by id")
    p_read.add_argument("--id", required=True, help="message id")

    p_send = sub.add_parser("send", help="Send an email")
    p_send.add_argument("--to", required=True)
    p_send.add_argument("--subject", required=True)
    p_send.add_argument("--body", required=True)

    p_comp = sub.add_parser("compose", help="Create a draft")
    p_comp.add_argument("--to", required=True)
    p_comp.add_argument("--subject", required=True)
    p_comp.add_argument("--body", required=True)

    p_reply = sub.add_parser("reply", help="Reply to a message")
    p_reply.add_argument("--id", required=True, help="message id to reply to")
    p_reply.add_argument("--body", required=True, help="reply body")
    p_reply.add_argument("--no-quote", action="store_true", help="do not include quoted original")

    args = parser.parse_args()
    asyncio.run(run_action(args))


if __name__ == "__main__":
    main()
