# Google Calendar MCP統合セットアップガイド

このガイドでは、音声AIエージェントにGoogleカレンダー機能を統合する手順を説明します。

## 前提条件

- Python 3.8以上
- Googleアカウント
- Google Cloud Platform プロジェクト

## 1. Google Cloud Console設定

### 1.1 プロジェクト作成

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成、または既存プロジェクトを選択

### 1.2 Google Calendar APIを有効化

1. 「APIとサービス」→「ライブラリ」を開く
2. "Google Calendar API"を検索
3. 「有効にする」をクリック

### 1.3 OAuth 2.0認証情報を作成

1. 「APIとサービス」→「認証情報」を開く
2. 「+ 認証情報を作成」→「OAuth クライアント ID」をクリック
3. **アプリケーションタイプ：デスクトップアプリケーション**を選択
4. 名前を入力（例：Calendar MCP Local）
5. 「作成」をクリック

### 1.4 認証情報の取得

作成完了後、ポップアップに表示される：
- **クライアント ID**
- **クライアント シークレット**

これらをコピーして保存してください。

### 1.5 OAuth同意画面の設定

1. 「APIとサービス」→「OAuth同意画面」を開く
2. User Typeを「外部」に設定
3. 必要情報を入力：
   - アプリ名
   - ユーザーサポートメール
   - デベロッパー連絡先

4. **スコープの追加**：
   - 「スコープを追加または削除」をクリック
   - `calendar`で検索
   - `.../auth/calendar`（読み取り・書き込みアクセス）を追加
   - 「更新」をクリック

5. **テストユーザーの追加**：
   - 使用するGoogleアカウントのメールアドレスを追加

6. 「保存して続行」

### 1.6 リダイレクトURIの設定

1. 「APIとサービス」→「認証情報」を開く
2. 作成したOAuth 2.0クライアントIDをクリック
3. 「承認済みのリダイレクト URI」セクションで「+ URI を追加」
4. 以下を追加：
   ```
   http://localhost:8080/oauth2callback
   ```
5. 「保存」をクリック

## 2. ローカル環境設定

### 2.1 環境変数の設定

`mcp_servers/calendar-mcp/.env`ファイルを作成：

```bash
cd mcp_servers/calendar-mcp
cp env.example .env
```

`.env`ファイルを編集して以下を設定：

```dotenv
# Google OAuth 2.0 クライアント認証情報
GOOGLE_CLIENT_ID='あなたのクライアントID'
GOOGLE_CLIENT_SECRET='あなたのクライアントシークレット'

# トークン保存先（自動生成）
TOKEN_FILE_PATH='.gcp-saved-tokens.json'

# OAuthコールバックポート（リダイレクトURIと一致させる）
OAUTH_CALLBACK_PORT=8080

# カレンダーAPIスコープ
CALENDAR_SCOPES='https://www.googleapis.com/auth/calendar'
```

### 2.2 初回認証の実行

calendar-mcpサーバーを手動で起動して初回OAuth認証を完了します：

```bash
cd mcp_servers/calendar-mcp
python run_server.py
```

**認証フロー：**

1. ターミナルに認証URLが表示される
2. ブラウザが自動的に開く（開かない場合はURLをコピーしてブラウザに貼り付け）
3. Googleアカウントでログイン
4. カレンダーアクセスを許可
5. リダイレクト後、トークンが自動保存される（`.gcp-saved-tokens.json`）
6. サーバー起動確認後、`Ctrl+C`で停止

**注意：**
- トークンファイル（`.gcp-saved-tokens.json`）は自動的に`.gitignore`に追加されます
- このファイルは絶対に公開しないでください

## 3. 音声AIエージェントへの統合

### 3.1 ツールの登録

`src/main.py`を編集して、calendar_mcp_toolを登録：

```python
from src.tools.calendar_mcp_tool import CalendarMCPTool

# ツールレジストリに追加
async def initialize_tools():
    # ... 既存のツール ...

    # カレンダーMCPツール
    calendar_tool = CalendarMCPTool()
    await calendar_tool.initialize()
    agent.register_tool(calendar_tool)
```

### 3.2 動作確認

サーバーを起動：

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

ブラウザで`http://localhost:8000`を開き、音声コマンドでテスト：

**テストコマンド例：**
- 「今日の予定を教えて」→ 予定一覧を取得
- 「明日の午後3時に会議の予定を作って」→ イベント作成
- 「今週の空き時間を確認して」→ 空き時間検索

## 4. 利用可能な音声コマンド

### 予定確認
- 「今日の予定を教えて」
- 「明日のスケジュールは？」
- 「今週の予定を確認して」

### 予定作成
- 「明日の午後3時に会議を入れて」
- 「来週の月曜10時から打ち合わせを設定して」
- 「金曜日にランチミーティングを追加して」

### 空き時間確認
- 「今日の空き時間を教えて」
- 「明日の午後は空いてる？」

### 予定変更・削除
- 「明日の会議を削除して」
- 「午後3時の予定を4時に変更して」

## 5. トラブルシューティング

### エラー: "OAuth consent required"

**原因:** 初回認証が完了していない

**解決方法:**
```bash
cd mcp_servers/calendar-mcp
python run_server.py
```
ブラウザで認証を完了してください。

### エラー: "Invalid redirect URI"

**原因:** リダイレクトURIの設定ミス

**解決方法:**
1. Google Cloud Consoleで認証情報を確認
2. リダイレクトURIが`http://localhost:8080/oauth2callback`であることを確認
3. `.env`の`OAUTH_CALLBACK_PORT`が`8080`であることを確認

### エラー: "Token expired"

**原因:** アクセストークンの期限切れ

**解決方法:**
トークンは自動更新されますが、問題がある場合は再認証：
```bash
rm mcp_servers/calendar-mcp/.gcp-saved-tokens.json
cd mcp_servers/calendar-mcp
python run_server.py
```

### エラー: "Calendar API not enabled"

**原因:** Google Calendar APIが有効化されていない

**解決方法:**
1. Google Cloud Console → 「APIとサービス」→「ライブラリ」
2. "Google Calendar API"を検索して有効化

## 6. セキュリティに関する注意

⚠️ **重要：以下のファイルは絶対にGitにコミットしないでください**

- `mcp_servers/calendar-mcp/.env`
- `mcp_servers/calendar-mcp/.gcp-saved-tokens.json`

これらは自動的に`.gitignore`に追加されていますが、必ず確認してください。

## 7. 参考リンク

- [Google Calendar API Documentation](https://developers.google.com/calendar/api/guides/overview)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [calendar-mcp GitHub](https://github.com/deciduus/calendar-mcp)
