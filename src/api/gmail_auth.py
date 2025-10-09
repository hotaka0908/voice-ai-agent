"""
Gmail & Calendar Authentication API Router

マルチユーザー対応のGmail & Calendar OAuth認証エンドポイント
1度の認証でGmailとCalendar両方のアクセス権を取得
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from loguru import logger

from src.dependencies.session import get_session_id
from src.middleware.session import session_manager

router = APIRouter()

# Gmail & Calendar APIのスコープ
# 注: Google OAuth では同じクライアントで複数のスコープを要求する必要がある
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/calendar'
]

# 一時的に認証中のセッションを記録（state → session_id）
# 本番環境ではRedisなどを使用推奨
auth_states = {}


@router.get("/api/gmail/auth/start")
async def gmail_auth_start(session_id: str = Depends(get_session_id)):
    """
    Gmail & Calendar OAuth認証を開始

    1度の認証でGmailとCalendar両方のアクセス権を取得します

    Args:
        session_id: セッションID（ヘッダーから自動取得）

    Returns:
        dict: 認証URL とstate

    Raises:
        HTTPException: 認証情報ファイルが見つからない場合
    """
    logger.info(f"Starting Gmail & Calendar OAuth for session: {session_id}")

    # 認証情報ファイルの確認（環境変数または物理ファイル）
    credentials_file = "data/gmail_credentials.json"
    credentials_json = os.getenv('GMAIL_CREDENTIALS_JSON')

    if not credentials_json and not os.path.exists(credentials_file):
        logger.error("Gmail credentials not found in environment or file")
        raise HTTPException(
            status_code=500,
            detail="Gmail credentials not configured. Please set GMAIL_CREDENTIALS_JSON environment variable or provide credentials file."
        )

    try:
        # リダイレクトURI（環境に応じて動的に変更）
        app_url = os.getenv('APP_URL', 'http://localhost:8000')
        redirect_uri = f"{app_url}/api/gmail/auth/callback"

        logger.debug(f"Redirect URI: {redirect_uri}")

        # OAuth2フローの作成（環境変数またはファイルから）
        if credentials_json:
            import json
            credentials_dict = json.loads(credentials_json)
            flow = Flow.from_client_config(
                credentials_dict,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )
            logger.debug("Using credentials from environment variable")
        else:
            flow = Flow.from_client_secrets_file(
                credentials_file,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )
            logger.debug("Using credentials from file")

        # 認証URLの生成
        auth_url, state = flow.authorization_url(
            access_type='offline',  # リフレッシュトークンを取得
            include_granted_scopes='true',
            prompt='consent'  # 常に同意画面を表示（refresh_token取得のため）
        )

        # stateとsession_idを紐付け（CSRF対策 & セッション追跡）
        auth_states[state] = session_id
        logger.info(f"Auth state created: {state} → session: {session_id}")

        return {
            "auth_url": auth_url,
            "state": state
        }

    except Exception as e:
        logger.error(f"Failed to start Gmail auth: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start authentication: {str(e)}"
        )


@router.get("/api/gmail/auth/callback")
async def gmail_auth_callback(code: str, state: str):
    """
    Gmail & Calendar OAuth認証のコールバック

    Google認証ページから戻ってくるエンドポイント

    Args:
        code: 認証コード
        state: CSRF対策トークン

    Returns:
        HTMLResponse: 成功/失敗ページ
    """
    logger.info(f"Gmail & Calendar OAuth callback received: state={state}")

    # stateからsession_idを取得
    session_id = auth_states.get(state)
    if not session_id:
        logger.error(f"Invalid auth state: {state}")
        return HTMLResponse("""
            <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: #f44336;
                            color: white;
                        }
                        .container {
                            text-align: center;
                            padding: 2rem;
                            background: rgba(255, 255, 255, 0.1);
                            border-radius: 10px;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>❌ エラー</h1>
                        <p>無効な認証リクエストです。</p>
                        <p>もう一度お試しください。</p>
                        <button onclick="window.close()">閉じる</button>
                    </div>
                </body>
            </html>
        """, status_code=400)

    try:
        # 認証コードをトークンに交換
        credentials_file = "data/gmail_credentials.json"
        credentials_json = os.getenv('GMAIL_CREDENTIALS_JSON')
        app_url = os.getenv('APP_URL', 'http://localhost:8000')
        redirect_uri = f"{app_url}/api/gmail/auth/callback"

        # OAuth2フローの作成（環境変数またはファイルから）
        if credentials_json:
            import json
            credentials_dict = json.loads(credentials_json)
            flow = Flow.from_client_config(
                credentials_dict,
                scopes=SCOPES,
                redirect_uri=redirect_uri,
                state=state
            )
        else:
            flow = Flow.from_client_secrets_file(
                credentials_file,
                scopes=SCOPES,
                redirect_uri=redirect_uri,
                state=state
            )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        # トークンをユーザーごとに保存（GmailとCalendar共通）
        token_path = session_manager.get_gmail_token_path(session_id)
        calendar_token_path = session_manager.get_calendar_token_path(session_id)

        # 両方のパスに保存（Gmail ToolとCalendar Toolで使用）
        with open(token_path, 'w') as token_file:
            token_file.write(credentials.to_json())
        with open(calendar_token_path, 'w') as token_file:
            token_file.write(credentials.to_json())

        logger.info(f"Gmail & Calendar token saved for session: {session_id}")

        # 使用済みstateを削除
        del auth_states[state]

        # 成功ページを返す
        return HTMLResponse(f"""
            <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                        }}
                        .container {{
                            text-align: center;
                            padding: 2rem;
                            background: rgba(255, 255, 255, 0.1);
                            border-radius: 10px;
                            backdrop-filter: blur(10px);
                        }}
                        h1 {{ margin: 0 0 1rem 0; }}
                        .icon {{ font-size: 4rem; margin-bottom: 1rem; }}
                        .message {{ font-size: 1.2rem; margin: 1rem 0; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">✅</div>
                        <h1>Gmail & Calendar連携が完了しました！</h1>
                        <p class="message">GmailとCalendarが両方使えるようになりました。<br>このウィンドウを閉じてください。</p>
                    </div>
                    <script>
                        // 親ウィンドウに成功を通知
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'gmail_auth_success',
                                sessionId: '{session_id}'
                            }}, '*');
                        }}

                        // 2秒後に自動的にウィンドウを閉じる
                        setTimeout(() => {{
                            window.close();
                        }}, 2000);
                    </script>
                </body>
            </html>
        """)

    except Exception as e:
        logger.error(f"Gmail auth callback failed: {e}")

        # 使用済みstateを削除
        if state in auth_states:
            del auth_states[state]

        return HTMLResponse(f"""
            <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: #f44336;
                            color: white;
                        }}
                        .container {{
                            text-align: center;
                            padding: 2rem;
                            background: rgba(255, 255, 255, 0.1);
                            border-radius: 10px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>❌ 認証エラー</h1>
                        <p>認証に失敗しました。</p>
                        <p>{str(e)}</p>
                        <button onclick="window.close()">閉じる</button>
                    </div>
                </body>
            </html>
        """, status_code=500)


@router.get("/api/gmail/status")
async def gmail_status(session_id: str = Depends(get_session_id)):
    """
    Gmail & Calendar連携状態を取得

    Args:
        session_id: セッションID（ヘッダーから自動取得）

    Returns:
        dict: 連携状態とメールアドレス
    """
    logger.debug(f"Checking Gmail & Calendar status for session: {session_id}")

    token_path = session_manager.get_gmail_token_path(session_id)

    if not os.path.exists(token_path):
        logger.info(f"No Gmail & Calendar token found for session: {session_id}")
        return {"connected": False, "email": None}

    try:
        # トークンを読み込み
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # トークンの有効性確認
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info(f"Refreshing Gmail token for session: {session_id}")
                # トークンをリフレッシュ
                creds.refresh(Request())

                # 更新したトークンを保存
                with open(token_path, 'w') as token_file:
                    token_file.write(creds.to_json())

                logger.info(f"Gmail token refreshed for session: {session_id}")
            else:
                logger.warning(f"Invalid Gmail token for session: {session_id}")
                return {"connected": False, "email": None}

        # メールアドレスを取得
        email = get_user_email(creds)
        return {"connected": True, "email": email}

    except Exception as e:
        logger.error(f"Failed to check Gmail status: {e}")
        return {"connected": False, "email": None}


@router.post("/api/gmail/disconnect")
async def gmail_disconnect(session_id: str = Depends(get_session_id)):
    """
    Gmail & Calendar連携を解除

    Args:
        session_id: セッションID（ヘッダーから自動取得）

    Returns:
        dict: 成功メッセージ
    """
    logger.info(f"Disconnecting Gmail & Calendar for session: {session_id}")

    token_path = session_manager.get_gmail_token_path(session_id)
    calendar_token_path = session_manager.get_calendar_token_path(session_id)

    # 両方のトークンを削除
    if os.path.exists(token_path):
        os.remove(token_path)
        logger.info(f"Gmail token removed for session: {session_id}")

    if os.path.exists(calendar_token_path):
        os.remove(calendar_token_path)
        logger.info(f"Calendar token removed for session: {session_id}")

    return {"success": True, "message": "Gmail & Calendar連携を解除しました"}


def get_user_email(credentials: Credentials) -> str:
    """
    認証情報からユーザーのメールアドレスを取得

    Args:
        credentials: Google OAuth認証情報

    Returns:
        str: メールアドレス
    """
    try:
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        return profile.get('emailAddress', 'unknown@example.com')
    except Exception as e:
        logger.error(f"Failed to get user email: {e}")
        return 'unknown@example.com'
