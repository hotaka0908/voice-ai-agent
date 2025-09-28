"""
Gmail Tool - Gmail API連携ツール

メールの確認、作成、送信機能を提供する
"""

import os
import json
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter, ToolSchema

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    logger.warning("Gmail dependencies not available. Install with: pip install google-auth google-auth-oauthlib google-api-python-client")


class GmailTool(Tool):
    """Gmail API連携ツール"""

    @property
    def name(self) -> str:
        return "gmail"

    @property
    def description(self) -> str:
        return "Gmailでメールの確認、作成、送信を行う"

    @property
    def category(self) -> str:
        return "communication"

    @property
    def requires_auth(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return False

    def __init__(self):
        super().__init__()

        # Gmail API の設定
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.compose'
        ]
        self.credentials_file = "data/gmail_credentials.json"
        self.token_file = "data/gmail_token.json"
        self.service = None

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description=(
                        "実行する操作: 'list' (メール一覧取得), 'read' (特定メール読み取り), "
                        "'send' (メール送信), 'compose' (下書き作成), 'reply' (返信)"
                    ),
                    required=True
                ),
                ToolParameter(
                    name="query",
                    type="string",
                    description="メール検索クエリ（action='list'の場合）。例: 'is:unread', 'from:example@gmail.com', 'subject:重要'",
                    required=False
                ),
                ToolParameter(
                    name="message_id",
                    type="string",
                    description="メッセージID（action='read' または 'reply' の場合。省略時は最新1件を自動選択。'query'併用可）",
                    required=False
                ),
                ToolParameter(
                    name="to",
                    type="string",
                    description="送信先メールアドレス（action='send'/'compose'の場合）",
                    required=False
                ),
                ToolParameter(
                    name="subject",
                    type="string",
                    description="メールの件名（action='send'/'compose'の場合）",
                    required=False
                ),
                ToolParameter(
                    name="body",
                    type="string",
                    description="メールの本文（action='send'/'compose'/'reply'の場合）",
                    required=False
                ),
                ToolParameter(
                    name="reply_quote",
                    type="boolean",
                    description="返信時に引用を含めるか（action='reply'の場合、デフォルト: true）",
                    required=False,
                    default=True
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="取得する最大メール数（action='list'の場合、デフォルト10）",
                    required=False
                )
            ]
        )

    async def _initialize_impl(self) -> bool:
        """Gmail API の初期化"""
        if not GMAIL_AVAILABLE:
            logger.warning("Gmail API libraries not available")
            return False

        try:
            # データディレクトリの作成
            os.makedirs("data", exist_ok=True)

            # 認証情報の確認
            if not os.path.exists(self.credentials_file):
                logger.warning(f"Gmail credentials file not found: {self.credentials_file}")
                logger.info("Please download OAuth 2.0 client credentials from Google Cloud Console")
                return False

            # サービスの初期化（認証は実行時に行う）
            logger.info("Gmail Tool initialized (authentication will be done on first use)")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Gmail Tool: {e}")
            return False

    async def _authenticate(self) -> bool:
        """Gmail API認証"""
        try:
            creds = None

            # 既存のトークンファイルがあるかチェック
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)

            # 認証情報が無効または期限切れの場合
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # トークンをリフレッシュ
                    creds.refresh(Request())
                else:
                    # 新しい認証フローを開始
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)

                # トークンを保存
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())

            # Gmail API サービスを構築
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API authentication successful")
            return True

        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Gmail操作の実行"""
        if not GMAIL_AVAILABLE:
            return ToolResult(
                success=False,
                result="",
                error="Gmail API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-api-python-client"
            )

        action = parameters.get("action", "").lower()

        # 認証確認
        if not self.service:
            if not await self._authenticate():
                return ToolResult(
                    success=False,
                    result="",
                    error="Gmail認証に失敗しました。認証情報を確認してください。"
                )

        try:
            if action == "list":
                return await self._list_emails(parameters)
            elif action == "read":
                return await self._read_email(parameters)
            elif action == "send":
                return await self._send_email(parameters)
            elif action == "compose":
                return await self._compose_draft(parameters)
            elif action == "reply":
                return await self._reply_email(parameters)
            else:
                return ToolResult(
                    success=False,
                    result="",
                    error=f"不明なアクション: {action}. 使用可能: list, read, send, compose, reply"
                )

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return ToolResult(
                success=False,
                result="",
                error=f"Gmail APIエラー: {e}"
            )
        except Exception as e:
            logger.error(f"Gmail tool error: {e}")
            return ToolResult(
                success=False,
                result="",
                error=f"Gmail操作エラー: {e}"
            )

    async def _list_emails(self, parameters: Dict[str, Any]) -> ToolResult:
        """メール一覧取得"""
        query = parameters.get("query", "")
        max_results = parameters.get("max_results", 10)

        try:
            # メッセージ一覧を取得（401等の認証エラー時は再認証して1回だけ再試行）
            try:
                results = self.service.users().messages().list(
                    userId='me', q=query, maxResults=max_results
                ).execute()
            except HttpError as e:
                if getattr(e, 'resp', None) and getattr(e.resp, 'status', None) in (401, 403):
                    logger.warning("Gmail API auth error on list; reauth and retry")
                    if await self._authenticate():
                        results = self.service.users().messages().list(
                            userId='me', q=query, maxResults=max_results
                        ).execute()
                    else:
                        raise
                else:
                    raise

            messages = results.get('messages', [])

            if not messages:
                return ToolResult(
                    success=True,
                    result="該当するメールが見つかりませんでした。"
                )

            # 各メッセージの詳細を取得
            email_list = []
            for msg in messages[:max_results]:
                msg_detail = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()

                headers = {h['name']: h['value'] for h in msg_detail['payload']['headers']}

                email_info = {
                    'id': msg['id'],
                    'from': headers.get('From', '不明'),
                    'subject': headers.get('Subject', '件名なし'),
                    'date': headers.get('Date', '日付不明')
                }
                email_list.append(email_info)

            # 結果をフォーマット
            result_text = f"📧 メール一覧 ({len(email_list)}件)\n\n"
            for i, email in enumerate(email_list, 1):
                result_text += f"{i}. **{email['subject']}**\n"
                result_text += f"   差出人: {email['from']}\n"
                result_text += f"   日時: {email['date']}\n"
                result_text += f"   ID: {email['id']}\n\n"

            # メタデータにメールIDを含める（ID抽出用）
            metadata = {"latest_email_id": email_list[0]['id'] if email_list else None}

            return ToolResult(success=True, result=result_text, metadata=metadata)

        except Exception as e:
            return ToolResult(
                success=False,
                result="",
                error=f"メール一覧取得エラー: {e}"
            )

    async def _read_email(self, parameters: Dict[str, Any]) -> ToolResult:
        """特定メールの読み取り"""
        message_id = parameters.get("message_id")
        query = parameters.get("query", "")

        # message_id 未指定なら最新1件を自動選択（任意の検索クエリに基づく）
        if not message_id:
            try:
                list_params = {"userId": 'me', "maxResults": 1}
                if query:
                    list_params["q"] = query
                results = self.service.users().messages().list(**list_params).execute()
                messages = results.get('messages', [])
                if messages:
                    message_id = messages[0]['id']
                else:
                    return ToolResult(success=True, result="該当するメールが見つかりませんでした。")
            except Exception as e:
                return ToolResult(success=False, result="", error=f"メール検索エラー: {e}")

        try:
            # メッセージ詳細を取得（401等の認証エラー時は再認証して再試行）
            try:
                message = self.service.users().messages().get(
                    userId='me', id=message_id, format='full'
                ).execute()
            except HttpError as e:
                if getattr(e, 'resp', None) and getattr(e.resp, 'status', None) in (401, 403):
                    logger.warning("Gmail API auth error on read; reauth and retry")
                    if await self._authenticate():
                        message = self.service.users().messages().get(
                            userId='me', id=message_id, format='full'
                        ).execute()
                    else:
                        raise
                else:
                    raise

            # ヘッダー情報を取得
            headers = {h['name']: h['value'] for h in message['payload']['headers']}

            # 本文を取得
            body = self._extract_body(message['payload'])

            # 結果をフォーマット
            result_text = f"📧 **メール詳細**\n\n"
            result_text += f"**件名**: {headers.get('Subject', '件名なし')}\n"
            result_text += f"**差出人**: {headers.get('From', '不明')}\n"
            result_text += f"**宛先**: {headers.get('To', '不明')}\n"
            result_text += f"**日時**: {headers.get('Date', '日付不明')}\n\n"
            result_text += f"**本文**:\n{body}\n"

            return ToolResult(success=True, result=result_text)

        except Exception as e:
            return ToolResult(
                success=False,
                result="",
                error=f"メール読み取りエラー: {e}"
            )

    async def _send_email(self, parameters: Dict[str, Any]) -> ToolResult:
        """メール送信"""
        to = parameters.get("to")
        subject = parameters.get("subject")
        body = parameters.get("body")

        if not all([to, subject, body]):
            return ToolResult(
                success=False,
                result="",
                error="to, subject, body が全て必要です"
            )

        try:
            # メッセージを作成
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            # Base64エンコード
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()

            # メール送信（401等の認証エラー時は再認証して再試行）
            try:
                sent_message = self.service.users().messages().send(
                    userId='me', body={'raw': raw_message}
                ).execute()
            except HttpError as e:
                if getattr(e, 'resp', None) and getattr(e.resp, 'status', None) in (401, 403):
                    logger.warning("Gmail API auth error on send; reauth and retry")
                    if await self._authenticate():
                        sent_message = self.service.users().messages().send(
                            userId='me', body={'raw': raw_message}
                        ).execute()
                    else:
                        raise
                else:
                    raise

            return ToolResult(
                success=True,
                result=f"✅ メールを送信しました\n宛先: {to}\n件名: {subject}\nメッセージID: {sent_message['id']}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                result="",
                error=f"メール送信エラー: {e}"
            )

    async def _compose_draft(self, parameters: Dict[str, Any]) -> ToolResult:
        """下書き作成"""
        to = parameters.get("to")
        subject = parameters.get("subject")
        body = parameters.get("body")

        if not all([to, subject, body]):
            return ToolResult(
                success=False,
                result="",
                error="to, subject, body が全て必要です"
            )

        try:
            # メッセージを作成
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            # Base64エンコード
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()

            # 下書きを作成（401等の認証エラー時は再認証して再試行）
            try:
                draft = self.service.users().drafts().create(
                    userId='me', body={'message': {'raw': raw_message}}
                ).execute()
            except HttpError as e:
                if getattr(e, 'resp', None) and getattr(e.resp, 'status', None) in (401, 403):
                    logger.warning("Gmail API auth error on compose; reauth and retry")
                    if await self._authenticate():
                        draft = self.service.users().drafts().create(
                            userId='me', body={'message': {'raw': raw_message}}
                        ).execute()
                    else:
                        raise
                else:
                    raise

            return ToolResult(
                success=True,
                result=f"📝 下書きを作成しました\n宛先: {to}\n件名: {subject}\n下書きID: {draft['id']}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                result="",
                error=f"下書き作成エラー: {e}"
            )

    def _extract_body(self, payload) -> str:
        """メールの本文を抽出"""
        body = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html':
                    # HTMLの場合は簡単にテキスト化
                    data = part['body']['data']
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                    # 簡単なHTML除去（本格的にはBeautifulSoupを使用）
                    import re
                    body = re.sub(r'<[^>]+>', '', html_body)
        else:
            if payload['body'].get('data'):
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')

        return body or "本文を取得できませんでした"

    async def _reply_email(self, parameters: Dict[str, Any]) -> ToolResult:
        """メール返信"""
        import re
        from email.utils import parseaddr

        message_id = parameters.get("message_id")
        body = parameters.get("body")
        quote = parameters.get("reply_quote", True)

        if not message_id or not body:
            return ToolResult(
                success=False,
                result="",
                error="message_id と body が必要です"
            )

        try:
            # 元メールの詳細を取得
            original = self.service.users().messages().get(
                userId='me', id=message_id, format='full'
            ).execute()

            thread_id = original.get('threadId')
            headers = {h['name']: h['value'] for h in original['payload'].get('headers', [])}

            reply_to = headers.get('Reply-To') or headers.get('From')
            name, addr = parseaddr(reply_to or "")
            to_addr = addr or reply_to or ""
            if not to_addr:
                return ToolResult(success=False, result="", error="返信先アドレスを特定できませんでした")

            subject = headers.get('Subject', 'No subject')
            if not re.match(r'^(Re:|RE:)', subject):
                subject = f"Re: {subject}"

            original_msg_id = headers.get('Message-ID') or headers.get('Message-Id')
            references = headers.get('References', '')
            if original_msg_id:
                references = (references + ' ' + original_msg_id).strip()

            # 引用文作成（簡易）
            quoted = ""
            if quote:
                orig_body = self._extract_body(original.get('payload', {}))
                quoted_lines = '\n'.join([f"> {line}" for line in orig_body.splitlines()])
                quoted = f"\n\n----- Original Message -----\n{quoted_lines}"

            # メッセージ作成
            reply = MIMEText((body + quoted).encode('utf-8'), _charset='utf-8')
            reply['to'] = to_addr
            reply['subject'] = subject
            if original_msg_id:
                reply['In-Reply-To'] = original_msg_id
            if references:
                reply['References'] = references

            raw_message = base64.urlsafe_b64encode(reply.as_bytes()).decode()

            sent = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message, **({'threadId': thread_id} if thread_id else {})}
            ).execute()

            return ToolResult(
                success=True,
                result=f"✅ 返信を送信しました\n宛先: {to_addr}\n件名: {subject}\nメッセージID: {sent.get('id')}\nスレッドID: {sent.get('threadId')}"
            )

        except Exception as e:
            logger.error(f"メール返信エラー: {e}")
            return ToolResult(success=False, result="", error=f"メール返信エラー: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """ツールの状態を取得"""
        return {
            "initialized": self.is_initialized,
            "authenticated": self.service is not None,
            "gmail_available": GMAIL_AVAILABLE,
            "credentials_exists": os.path.exists(self.credentials_file),
            "token_exists": os.path.exists(self.token_file)
        }

    async def cleanup(self):
        """リソースのクリーンアップ"""
        self.service = None
        logger.info("Gmail Tool cleanup completed")
