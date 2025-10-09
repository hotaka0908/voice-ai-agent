# Gmail連携機能 実装計画（マルチユーザー対応版）

## 📋 概要

**目的:** URLを共有すれば、どんな人でも自分のGmailと連携して音声アシスタントを使える機能を実装する

**重要:** 複数ユーザーが同時に利用できるよう、セッション管理とユーザー識別を実装します。

## 🚨 解決すべき課題

### 現在の計画の問題
- ❌ 全ユーザーが同じトークンファイルを使用（上書きされる）
- ❌ ユーザー識別がない
- ❌ セッション管理がない

### マルチユーザー対応の要件
- ✅ 各ユーザーを一意に識別
- ✅ ユーザーごとにトークンを分離保存
- ✅ セッションでユーザーを追跡
- ✅ 他のユーザーのデータにアクセス不可

## 🏗️ アーキテクチャ設計（マルチユーザー版）

### 1. ユーザー識別方法

**選択肢:**

#### A. セッションID（推奨）
- ブラウザごとに一意のセッションIDを生成
- Cookieまたは LocalStorage に保存
- サーバー側でセッションIDとトークンを紐付け

**メリット:**
- ログイン不要
- シンプル
- すぐに使える

**デメリット:**
- Cookieクリアでセッション喪失
- 端末ごとに再連携が必要

#### B. Googleアカウントベース認証
- Googleアカウント自体をユーザーIDとして使用
- OAuth認証後、email をユーザーIDにする

**メリット:**
- 端末が変わっても同じアカウント
- セキュアな認証

**デメリット:**
- 実装が複雑
- ログインフローが増える

### 推奨: **A. セッションID方式**（Phase 1）

```
[ユーザー訪問]
    ↓
[セッションID生成（UUID）]
    ↓
[Cookieに保存]
    ↓
[Gmail連携時: session_id + gmail_token を保存]
```

## 🔧 実装詳細

### A. セッション管理

#### 1. セッション初期化（フロントエンド）

```javascript
// static/js/session.js
class SessionManager {
    constructor() {
        this.sessionId = this.getOrCreateSessionId();
    }

    getOrCreateSessionId() {
        // LocalStorageからセッションIDを取得
        let sessionId = localStorage.getItem('voiceagent_session_id');

        if (!sessionId) {
            // 新規セッションID生成（UUID v4）
            sessionId = this.generateUUID();
            localStorage.setItem('voiceagent_session_id', sessionId);
            console.log('🆕 New session created:', sessionId);
        } else {
            console.log('♻️  Existing session:', sessionId);
        }

        return sessionId;
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    getSessionId() {
        return this.sessionId;
    }
}

// グローバルインスタンス
window.sessionManager = new SessionManager();
```

#### 2. すべてのAPIリクエストにセッションIDを含める

```javascript
// APIリクエスト時
async function apiRequest(url, options = {}) {
    const sessionId = window.sessionManager.getSessionId();

    // ヘッダーにセッションIDを追加
    options.headers = {
        ...options.headers,
        'X-Session-ID': sessionId
    };

    return fetch(url, options);
}
```

### B. バックエンド実装

#### 1. セッション管理ミドルウェア

```python
# src/middleware/session.py
from fastapi import Request, HTTPException
from typing import Optional
import os
import json

class SessionManager:
    """セッション管理"""

    def __init__(self):
        self.sessions_dir = "data/sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)

    def get_session_id(self, request: Request) -> Optional[str]:
        """リクエストからセッションIDを取得"""
        return request.headers.get('X-Session-ID')

    def validate_session_id(self, session_id: str) -> bool:
        """セッションIDの形式を検証"""
        if not session_id or len(session_id) != 36:
            return False
        # UUID形式の簡易チェック
        return session_id.count('-') == 4

    def get_user_data_path(self, session_id: str, data_type: str) -> str:
        """ユーザーデータのパスを取得"""
        user_dir = os.path.join(self.sessions_dir, session_id)
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, f"{data_type}.json")

    def get_gmail_token_path(self, session_id: str) -> str:
        """Gmailトークンのパスを取得"""
        return self.get_user_data_path(session_id, "gmail_token")

# グローバルインスタンス
session_manager = SessionManager()
```

#### 2. セッション依存性（FastAPI Dependency）

```python
# src/dependencies/session.py
from fastapi import Header, HTTPException

async def get_session_id(x_session_id: str = Header(None)) -> str:
    """セッションIDを取得・検証する依存性"""
    if not x_session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID is required. Please include X-Session-ID header."
        )

    if not session_manager.validate_session_id(x_session_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID format"
        )

    return x_session_id
```

#### 3. Gmail認証API（マルチユーザー対応版）

```python
# src/api/gmail_auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import os

router = APIRouter()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

# 一時的に認証中のセッションを記録（state → session_id）
auth_states = {}

@router.get("/api/gmail/auth/start")
async def gmail_auth_start(session_id: str = Depends(get_session_id)):
    """Gmail OAuth認証を開始"""

    # 認証情報ファイルの確認
    credentials_file = "data/gmail_credentials.json"
    if not os.path.exists(credentials_file):
        raise HTTPException(
            status_code=500,
            detail="Gmail credentials file not found. Please configure OAuth credentials."
        )

    # リダイレクトURI（環境に応じて動的に変更）
    app_url = os.getenv('APP_URL', 'http://localhost:8000')
    redirect_uri = f"{app_url}/api/gmail/auth/callback"

    # OAuth2フローの作成
    flow = Flow.from_client_secrets_file(
        credentials_file,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

    # 認証URLの生成
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # 常に同意画面を表示（refresh_token取得のため）
    )

    # stateとsession_idを紐付け（CSRF対策 & セッション追跡）
    auth_states[state] = session_id

    return {
        "auth_url": auth_url,
        "state": state
    }


@router.get("/api/gmail/auth/callback")
async def gmail_auth_callback(code: str, state: str):
    """Gmail OAuth認証のコールバック"""

    # stateからsession_idを取得
    session_id = auth_states.get(state)
    if not session_id:
        return HTMLResponse("""
            <html>
                <body>
                    <h1>エラー: 無効な認証リクエスト</h1>
                    <p>認証セッションが見つかりません。もう一度お試しください。</p>
                </body>
            </html>
        """)

    try:
        # 認証コードをトークンに交換
        credentials_file = "data/gmail_credentials.json"
        app_url = os.getenv('APP_URL', 'http://localhost:8000')
        redirect_uri = f"{app_url}/api/gmail/auth/callback"

        flow = Flow.from_client_secrets_file(
            credentials_file,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            state=state
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        # トークンをユーザーごとに保存
        token_path = session_manager.get_gmail_token_path(session_id)
        with open(token_path, 'w') as token_file:
            token_file.write(credentials.to_json())

        # 使用済みstateを削除
        del auth_states[state]

        # 成功ページを返す
        return HTMLResponse("""
            <html>
                <head>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                        }
                        .container {
                            text-align: center;
                            padding: 2rem;
                            background: rgba(255, 255, 255, 0.1);
                            border-radius: 10px;
                            backdrop-filter: blur(10px);
                        }
                        h1 { margin: 0 0 1rem 0; }
                        .icon { font-size: 4rem; margin-bottom: 1rem; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">✅</div>
                        <h1>Gmail連携が完了しました！</h1>
                        <p>このウィンドウを閉じてください。</p>
                    </div>
                    <script>
                        // 親ウィンドウに成功を通知
                        if (window.opener) {
                            window.opener.postMessage({
                                type: 'gmail_auth_success',
                                sessionId: '""" + session_id + """'
                            }, '*');
                        }

                        // 2秒後に自動的にウィンドウを閉じる
                        setTimeout(() => {
                            window.close();
                        }, 2000);
                    </script>
                </body>
            </html>
        """)

    except Exception as e:
        # 使用済みstateを削除
        if state in auth_states:
            del auth_states[state]

        return HTMLResponse(f"""
            <html>
                <body>
                    <h1>エラー: 認証に失敗しました</h1>
                    <p>{str(e)}</p>
                    <button onclick="window.close()">閉じる</button>
                </body>
            </html>
        """)


@router.get("/api/gmail/status")
async def gmail_status(session_id: str = Depends(get_session_id)):
    """Gmail連携状態を取得"""

    token_path = session_manager.get_gmail_token_path(session_id)

    if not os.path.exists(token_path):
        return {"connected": False, "email": None}

    try:
        # トークンを読み込み
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # トークンの有効性確認
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # トークンをリフレッシュ
                from google.auth.transport.requests import Request
                creds.refresh(Request())

                # 更新したトークンを保存
                with open(token_path, 'w') as token_file:
                    token_file.write(creds.to_json())

                # メールアドレスを取得
                email = get_user_email(creds)
                return {"connected": True, "email": email}
            else:
                return {"connected": False, "email": None}

        # メールアドレスを取得
        email = get_user_email(creds)
        return {"connected": True, "email": email}

    except Exception as e:
        logger.error(f"Failed to check Gmail status: {e}")
        return {"connected": False, "email": None}


@router.post("/api/gmail/disconnect")
async def gmail_disconnect(session_id: str = Depends(get_session_id)):
    """Gmail連携を解除"""

    token_path = session_manager.get_gmail_token_path(session_id)

    if os.path.exists(token_path):
        os.remove(token_path)

    return {"success": True, "message": "Gmail連携を解除しました"}


def get_user_email(credentials: Credentials) -> str:
    """認証情報からユーザーのメールアドレスを取得"""
    try:
        from googleapiclient.discovery import build
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        return profile.get('emailAddress', 'unknown@example.com')
    except Exception as e:
        logger.error(f"Failed to get user email: {e}")
        return 'unknown@example.com'
```

#### 4. Gmail Tool修正（セッション対応）

```python
# src/tools/gmail_tool.py の修正

class GmailTool(Tool):
    def __init__(self, session_id: str = None):
        super().__init__()
        self.session_id = session_id  # セッションIDを保持
        # ... 既存の実装 ...

    async def _authenticate(self, session_id: str = None) -> bool:
        """Gmail API認証（セッション対応）"""
        try:
            # セッションIDが指定されていればそれを使用
            if session_id:
                self.session_id = session_id

            # セッション管理からトークンパスを取得
            if self.session_id:
                self.token_file = session_manager.get_gmail_token_path(self.session_id)
            else:
                # フォールバック: 環境変数から読み込み（Railway対応）
                self.token_file = "data/gmail_token.json"

            # 既存の認証ロジック
            # ...
```

### C. フロントエンド修正

#### 1. セッションマネージャーの追加

```javascript
// app.js の初期化部分
async init() {
    try {
        console.log('Initializing Voice Agent...');

        // セッション管理の初期化（最初に実行）
        if (!window.sessionManager) {
            window.sessionManager = new SessionManager();
        }

        // UIの初期化
        await this.uiManager.init();
        // ... 既存の初期化処理
    }
}
```

#### 2. API呼び出しの修正

```javascript
// すべてのfetch呼び出しにセッションIDヘッダーを追加
async apiRequest(url, options = {}) {
    const sessionId = window.sessionManager.getSessionId();

    options.headers = {
        ...options.headers,
        'X-Session-ID': sessionId
    };

    return fetch(url, options);
}

// 使用例
async showGmailInfo() {
    const response = await this.apiRequest('/api/gmail/status');
    const data = await response.json();
    // ...
}
```

### D. データ構造

```
data/
├── gmail_credentials.json (全ユーザー共通のOAuth設定)
├── sessions/
│   ├── 12345678-abcd-4ef0-9012-345678901234/  (ユーザーA)
│   │   ├── gmail_token.json
│   │   └── personal_memory.json
│   ├── 87654321-dcba-4fe0-2109-876543210987/  (ユーザーB)
│   │   ├── gmail_token.json
│   │   └── personal_memory.json
│   └── ...
```

## 🔒 セキュリティ

### 1. セッションハイジャック対策
- セッションIDをHTTPS経由でのみ送信
- セッションIDの形式検証

### 2. データ分離
- ユーザーAは `sessions/A/` にのみアクセス
- ユーザーBは `sessions/B/` にのみアクセス
- パストラバーサル攻撃を防ぐ

### 3. トークン保護
- ファイルパーミッション `0600`
- `.gitignore` に `data/sessions/` を追加

## 📝 実装ステップ（Phase 1: マルチユーザー対応）

### ステップ1: セッション管理基盤
1. `SessionManager` クラス実装（フロントエンド）
2. セッションミドルウェア実装（バックエンド）
3. すべてのAPI呼び出しにセッションID追加

### ステップ2: Gmail認証API（マルチユーザー版）
1. `/api/gmail/auth/start` - state とセッションIDの紐付け
2. `/api/gmail/auth/callback` - セッションごとにトークン保存
3. `/api/gmail/status` - セッションのトークン確認
4. `/api/gmail/disconnect` - セッションのトークン削除

### ステップ3: Gmail Tool修正
1. セッションIDを受け取る
2. セッションごとのトークンパスを使用
3. 環境変数との併用（Railway対応維持）

### ステップ4: テスト
1. 複数ブラウザ/シークレットモードでテスト
2. 異なるGoogleアカウントで同時連携
3. セッションの独立性を確認

## ✅ これで実現できること

### シナリオ1: ユーザーAがアクセス
```
1. https://your-app.railway.app にアクセス
2. セッションID生成: session-A
3. Gmailと連携: account-A@gmail.com
4. メール一覧: account-Aのメールのみ表示
```

### シナリオ2: ユーザーBがアクセス（同時）
```
1. https://your-app.railway.app にアクセス
2. セッションID生成: session-B
3. Gmailと連携: account-B@gmail.com
4. メール一覧: account-Bのメールのみ表示
```

### 結果
- ✅ ユーザーA と ユーザーB のデータは完全に分離
- ✅ URLを共有するだけで誰でも利用可能
- ✅ 各ユーザーは自分のGmailにのみアクセス

## 🚀 デプロイ考慮事項

### Google Cloud Console設定
- **重要:** OAuth同意画面を「公開」に設定
- リダイレクトURI追加:
  - `http://localhost:8000/api/gmail/auth/callback` (開発)
  - `https://your-app.railway.app/api/gmail/auth/callback` (本番)

### Railway環境変数
```bash
APP_URL=https://your-app.railway.app
```

## 🎯 結論

**元の計画（シングルユーザー）:** ❌ 複数人で使えない

**修正版（マルチユーザー）:** ✅ URLを共有すれば誰でも自分のGmailで使える

この修正版で実装すれば、要件を満たせます！
