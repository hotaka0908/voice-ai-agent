# Gmail連携機能 実装計画

## 📋 概要

ユーザーが設定画面からGmailツールをクリックし、「連携する」ボタンを押すことで、自身のGmailアカウントと連携できる機能を実装します。

## 🎯 要件

### 現在の状態
- ✅ Gmail Toolは実装済み（環境変数から認証情報を読み込み）
- ✅ 設定画面にツール一覧が表示される
- ✅ Gmailツールをクリックすると`showGmailInfo()`が呼ばれる
- ⚠️ 現在は「未連携」と表示されるのみで、連携ボタンがない

### 目標
- ✅ 「未連携」状態で「連携する」ボタンを表示
- ✅ ボタンクリックでGoogle OAuth認証フローを開始
- ✅ 認証完了後、トークンを保存
- ✅ 連携済み状態に変更し、メールアドレスを表示
- ✅ 「連携解除」ボタンで解除可能

## 🏗️ アーキテクチャ設計

### 1. OAuth認証フロー

```
[フロントエンド] → [バックエンド] → [Google OAuth] → [バックエンド] → [フロントエンド]
     ①              ②                  ③               ④                ⑤
```

#### フロー詳細

1. **①ユーザーが「連携する」ボタンをクリック**
   - `GET /api/gmail/auth/start` を呼び出し

2. **②バックエンドが認証URLを生成**
   - Google OAuth2の認証URLを作成
   - `state`パラメータでCSRF対策
   - リダイレクトURIを設定（`/api/gmail/auth/callback`）

3. **③Googleの認証ページにリダイレクト**
   - ユーザーがGoogleアカウントでログイン
   - Gmail APIのアクセス許可を承認

4. **④コールバックで認証コードを受け取る**
   - `GET /api/gmail/auth/callback?code=...&state=...`
   - 認証コードをアクセストークン・リフレッシュトークンに交換
   - トークンをDBまたはファイルに保存

5. **⑤フロントエンドに結果を返す**
   - 成功ページを表示（自動的にウィンドウを閉じる）
   - 親ウィンドウに`postMessage`で通知

### 2. データフロー

```
Gmail OAuth Token
    ↓
data/users/{user_id}/gmail_token.json (ユーザー単位で保存)
    ↓
Gmail Tool が読み込み
    ↓
Gmail API にアクセス
```

## 🔧 実装詳細

### A. バックエンドAPI

#### 1. `/api/gmail/auth/start` (GET)
**目的:** OAuth認証フローを開始

```python
@app.get("/api/gmail/auth/start")
async def gmail_auth_start():
    """Gmail OAuth認証を開始"""
    # Google OAuth2 認証URLを生成
    flow = InstalledAppFlow.from_client_secrets_file(
        'data/gmail_credentials.json',
        scopes=['https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send'],
        redirect_uri='http://localhost:8000/api/gmail/auth/callback'
    )

    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    # stateをセッションに保存（CSRF対策）
    # セッション管理が必要

    return {"auth_url": auth_url, "state": state}
```

#### 2. `/api/gmail/auth/callback` (GET)
**目的:** Google OAuthコールバックを処理

```python
@app.get("/api/gmail/auth/callback")
async def gmail_auth_callback(code: str, state: str):
    """Gmail OAuth認証のコールバック"""
    # stateを検証（CSRF対策）

    # 認証コードをトークンに交換
    flow = InstalledAppFlow.from_client_secrets_file(
        'data/gmail_credentials.json',
        scopes=[...],
        redirect_uri='http://localhost:8000/api/gmail/auth/callback'
    )

    flow.fetch_token(code=code)
    credentials = flow.credentials

    # トークンを保存
    save_user_gmail_token(credentials)

    # 成功ページを返す
    return HTMLResponse("""
        <html>
            <body>
                <h1>Gmail連携が完了しました！</h1>
                <p>このウィンドウを閉じてください。</p>
                <script>
                    window.opener.postMessage({type: 'gmail_auth_success'}, '*');
                    setTimeout(() => window.close(), 2000);
                </script>
            </body>
        </html>
    """)
```

#### 3. `/api/gmail/status` (GET)
**目的:** 現在の連携状態を確認

```python
@app.get("/api/gmail/status")
async def gmail_status():
    """Gmail連携状態を取得"""
    # ユーザーのトークンファイルを確認
    token_path = get_user_gmail_token_path()

    if not os.path.exists(token_path):
        return {"connected": False}

    # トークンを読み込んで有効性確認
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # トークンをリフレッシュ
            creds.refresh(Request())
            save_credentials(creds)
            return {"connected": True, "email": get_user_email(creds)}
        else:
            return {"connected": False}

    return {"connected": True, "email": get_user_email(creds)}
```

#### 4. `/api/gmail/disconnect` (POST)
**目的:** Gmail連携を解除

```python
@app.post("/api/gmail/disconnect")
async def gmail_disconnect():
    """Gmail連携を解除"""
    token_path = get_user_gmail_token_path()

    if os.path.exists(token_path):
        os.remove(token_path)

    return {"success": True, "message": "Gmail連携を解除しました"}
```

### B. フロントエンドUI

#### 1. Gmailダイアログの改善

**現在の`showGmailInfo()`を拡張:**

```javascript
async showGmailInfo() {
    // ダイアログを開く
    document.getElementById('gmailDialog').style.display = 'flex';

    try {
        // 連携状態を確認
        const response = await fetch('/api/gmail/status');
        const data = await response.json();

        const gmailStatus = document.getElementById('gmailStatus');

        if (data.connected && data.email) {
            // 連携済み
            gmailStatus.innerHTML = `
                <div class="gmail-connected">
                    <div class="gmail-icon">✅</div>
                    <div class="gmail-email">${data.email}</div>
                    <button onclick="window.voiceAgent.disconnectGmail()" class="disconnect-btn">
                        連携解除
                    </button>
                </div>
            `;
        } else {
            // 未連携
            gmailStatus.innerHTML = `
                <div class="gmail-not-connected">
                    <div class="gmail-icon">📧</div>
                    <p>Gmailと連携していません</p>
                    <button onclick="window.voiceAgent.connectGmail()" class="connect-btn">
                        連携する
                    </button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Failed to load Gmail status:', error);
    }
}
```

#### 2. 連携処理

```javascript
async connectGmail() {
    try {
        // 認証URLを取得
        const response = await fetch('/api/gmail/auth/start');
        const data = await response.json();

        // ポップアップで認証ページを開く
        const width = 600;
        const height = 700;
        const left = (screen.width - width) / 2;
        const top = (screen.height - height) / 2;

        const authWindow = window.open(
            data.auth_url,
            'Gmail認証',
            `width=${width},height=${height},left=${left},top=${top}`
        );

        // postMessageで結果を受け取る
        window.addEventListener('message', async (event) => {
            if (event.data.type === 'gmail_auth_success') {
                console.log('✅ Gmail連携成功');

                // ダイアログを更新
                await this.showGmailInfo();

                // ツールリストを再読み込み
                await this.loadAvailableTools();
            }
        });

    } catch (error) {
        console.error('Failed to connect Gmail:', error);
        alert('Gmail連携に失敗しました');
    }
}
```

#### 3. 連携解除処理

```javascript
async disconnectGmail() {
    if (!confirm('Gmail連携を解除しますか？')) {
        return;
    }

    try {
        const response = await fetch('/api/gmail/disconnect', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            console.log('✅ Gmail連携解除成功');

            // ダイアログを更新
            await this.showGmailInfo();

            // ツールリストを再読み込み
            await this.loadAvailableTools();
        }
    } catch (error) {
        console.error('Failed to disconnect Gmail:', error);
        alert('Gmail連携解除に失敗しました');
    }
}
```

### C. ユーザー管理

#### ユーザー識別

**選択肢:**

1. **セッションベース** - Cookie/LocalStorageでユーザーIDを管理
2. **シングルユーザー** - 1ユーザーのみサポート（簡易版）
3. **ログイン機能** - 完全な認証システム

**推奨: シングルユーザーモード（Phase 1）**

```python
# data/gmail_token.json に保存（1ユーザーのみ）
def get_user_gmail_token_path():
    return "data/gmail_token.json"
```

**将来的: マルチユーザー対応（Phase 2）**

```python
# data/users/{user_id}/gmail_token.json に保存
def get_user_gmail_token_path(user_id: str):
    return f"data/users/{user_id}/gmail_token.json"
```

### D. セキュリティ対策

1. **CSRF対策**
   - `state`パラメータでランダムトークンを生成
   - セッションに保存して検証

2. **トークン保護**
   - ファイルパーミッション `0600` で保存
   - `.gitignore` に追加済み

3. **HTTPS必須（本番環境）**
   - Railwayでは自動的にHTTPSが有効

4. **リダイレクトURI検証**
   - Google Cloud Consoleに登録したURIのみ許可

## 📝 実装ステップ

### Phase 1: 基本連携機能（推奨）

1. **バックエンドAPI実装**
   - `/api/gmail/auth/start`
   - `/api/gmail/auth/callback`
   - `/api/gmail/status`
   - `/api/gmail/disconnect`

2. **フロントエンド実装**
   - `connectGmail()` - 連携開始
   - `disconnectGmail()` - 連携解除
   - `showGmailInfo()` - 状態表示の改善

3. **Gmail Tool修正**
   - `data/gmail_token.json` から自動読み込み
   - 環境変数との併用（Railway対応）

4. **テスト**
   - ローカルで連携フローをテスト
   - トークンリフレッシュのテスト

### Phase 2: 拡張機能（オプション）

1. **マルチユーザー対応**
   - ユーザーIDでトークンを分離

2. **連携状態の永続化**
   - データベースに保存

3. **エラーハンドリング改善**
   - より詳細なエラーメッセージ

## 🚀 デプロイ考慮事項

### ローカル開発

- リダイレクトURI: `http://localhost:8000/api/gmail/auth/callback`
- Google Cloud Consoleに登録

### Railway本番環境

- リダイレクトURI: `https://your-app.railway.app/api/gmail/auth/callback`
- Google Cloud Consoleに追加登録
- 環境変数 `APP_URL` で動的に切り替え

```python
REDIRECT_URI = os.getenv('APP_URL', 'http://localhost:8000') + '/api/gmail/auth/callback'
```

## ⚠️ 注意事項

1. **Google Cloud Console設定が必要**
   - リダイレクトURIを事前登録
   - OAuth同意画面の設定

2. **初回認証はブラウザ必須**
   - ユーザーが手動でGoogleアカウントにログイン

3. **トークン有効期限**
   - アクセストークン: 1時間
   - リフレッシュトークン: 無期限（自動更新）

4. **スコープの管理**
   - 必要最小限のスコープのみ要求
   - 現在: `gmail.readonly`, `gmail.send`, `gmail.compose`

## 📊 期待される動作

### 連携前
```
[設定画面]
  └ Gmail [未連携]
      └ クリック
          └ ダイアログ表示
              └ 「連携する」ボタン
```

### 連携中
```
[連携するボタン]
  └ ポップアップでGoogle認証
      └ ログイン & 許可
          └ コールバック
              └ トークン保存
                  └ ダイアログ更新
```

### 連携後
```
[設定画面]
  └ Gmail [連携済み]
      └ クリック
          └ ダイアログ表示
              └ メールアドレス表示
              └ 「連携解除」ボタン
```

---

**この計画でよろしいですか？承認後、実装を開始します。**
