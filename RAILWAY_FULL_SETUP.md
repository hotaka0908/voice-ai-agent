# Railway フル機能セットアップガイド

VoiceAgentをRailwayでGmail・Googleカレンダー統合を含むフル機能で動作させる手順

## 📋 必要な環境変数

Railwayのダッシュボード → Variables で以下を設定してください。

### 1. 必須API Keys

```bash
# OpenAI API (音声認識・音声合成・Vision)
OPENAI_API_KEY=your_openai_api_key_here

# Claude API (メインLLM)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 2. Gmail認証情報

```bash
# Gmail OAuth Credentials（data/gmail_credentials.json の内容）
# ローカルのdata/gmail_credentials.jsonファイルの内容をコピーしてください
GMAIL_CREDENTIALS_JSON='{"installed":{"client_id":"YOUR_CLIENT_ID.apps.googleusercontent.com","project_id":"YOUR_PROJECT_ID","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"YOUR_CLIENT_SECRET","redirect_uris":["http://localhost"]}}'

# Gmail OAuth Token（data/gmail_token.json の内容）
# ローカルのdata/gmail_token.jsonファイルの内容をコピーしてください
GMAIL_TOKEN_JSON='{"token": "ya29.YOUR_ACCESS_TOKEN", "refresh_token": "1//YOUR_REFRESH_TOKEN", "token_uri": "https://oauth2.googleapis.com/token", "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com", "client_secret": "YOUR_CLIENT_SECRET", "scopes": ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.compose"], "universe_domain": "googleapis.com", "account": "", "expiry": "2025-10-07T05:55:20.212625Z"}'
```

### 3. Googleカレンダー認証情報

```bash
# Calendar OAuth Client ID & Secret（mcp_servers/calendar-mcp/.env の内容）
# ローカルのmcp_servers/calendar-mcp/.envファイルから値をコピーしてください
GOOGLE_CLIENT_ID='YOUR_CALENDAR_CLIENT_ID.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET='YOUR_CALENDAR_CLIENT_SECRET'

# Calendar OAuth Token（mcp_servers/calendar-mcp/.gcp-saved-tokens.json の内容）
# ローカルのmcp_servers/calendar-mcp/.gcp-saved-tokens.jsonファイルの内容をコピーしてください
CALENDAR_TOKEN_JSON='{"token": "ya29.YOUR_CALENDAR_ACCESS_TOKEN", "refresh_token": "1//YOUR_CALENDAR_REFRESH_TOKEN", "token_uri": "https://oauth2.googleapis.com/token", "client_id": "YOUR_CALENDAR_CLIENT_ID.apps.googleusercontent.com", "client_secret": "YOUR_CALENDAR_CLIENT_SECRET", "scopes": ["https://www.googleapis.com/auth/calendar"], "universe_domain": "googleapis.com", "account": "", "expiry": "2025-10-03T13:15:28Z"}'

# Calendar API Scopes
CALENDAR_SCOPES='https://www.googleapis.com/auth/calendar'
```

### 4. オプション設定

```bash
# LLM設定
DEFAULT_LLM_PROVIDER=claude
DEFAULT_VOICE=alloy
DEFAULT_AI_MODE=assist

# ログ設定
LOG_LEVEL=INFO
```

## 🚀 セットアップ手順

### ステップ1: Railway プロジェクトにアクセス

1. [Railway Dashboard](https://railway.app/dashboard)を開く
2. VoiceAgentプロジェクトを選択
3. 「Variables」タブをクリック

### ステップ2: 環境変数を一括追加

上記の環境変数をコピー&ペーストで追加：

**注意事項:**
- JSON形式の変数（`GMAIL_CREDENTIALS_JSON`等）は、**シングルクォート**で囲む
- 改行を含めず、1行で入力
- トークンは期限切れの場合、ローカルで再生成して更新

### ステップ3: デプロイ確認

環境変数を保存すると、Railwayが自動的に再デプロイします。

**デプロイログで確認:**
```
✓ Building...
✓ Deploying...
✓ Live on: https://your-app.railway.app
```

### ステップ4: 動作確認

ブラウザで公開URLにアクセスして以下をテスト：

1. **Gmail機能**: 「未読メールを確認して」
2. **カレンダー機能**: 「今日の予定を教えて」
3. **音声認識・合成**: マイク入力と音声出力
4. **カメラ認識**: カメラボタンで画像分析

## 🔧 コードの自動対応

VoiceAgentのコードは環境変数から自動的に認証ファイルを読み込みます：

```python
# src/tools/gmail_tool.py
credentials_json = os.getenv('GMAIL_CREDENTIALS_JSON')
token_json = os.getenv('GMAIL_TOKEN_JSON')

# src/tools/calendar_mcp_tool.py
client_id = os.getenv('GOOGLE_CLIENT_ID')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
token_json = os.getenv('CALENDAR_TOKEN_JSON')
```

## ⚠️ セキュリティ注意事項

### トークンの機密性

- **絶対にGitHubにコミットしない**
- Railway環境変数は暗号化されて保存される
- トークンは定期的に更新される（refresh_tokenで自動更新）

### トークン更新が必要な場合

もしトークンが期限切れになった場合：

1. ローカルで認証ファイルを削除
   ```bash
   rm data/gmail_token.json
   rm mcp_servers/calendar-mcp/.gcp-saved-tokens.json
   ```

2. ローカルでVoiceAgentを起動して再認証
   ```bash
   uvicorn src.main:app --reload
   ```

3. 新しいトークンをRailway環境変数に再設定

## 📊 利用可能な全機能

Railwayでフル機能デプロイ後に使える機能：

### ✅ 音声・対話
- リアルタイム音声認識（OpenAI Whisper）
- 高品質音声合成（OpenAI TTS）
- WebSocket低遅延通信

### ✅ Gmail統合
- 未読メール確認
- メール検索（送信者・件名・本文）
- メール返信・送信
- 下書き作成

### ✅ Googleカレンダー統合
- 予定確認（今日・明日・今週）
- イベント作成
- 空き時間検索
- 予定変更・削除

### ✅ AI機能
- Claude/ChatGPT切り替え
- Vision API画像認識
- 性格タイプ分析
- 個人情報管理

### ✅ その他ツール
- アラーム設定
- 計算機能
- 時刻・日付確認
- ルールベース高速応答

## 🆘 トラブルシューティング

### Gmail/カレンダーが動作しない

**確認事項:**
1. 環境変数が正しく設定されているか
2. JSON形式が壊れていないか（シングルクォートで囲まれているか）
3. トークンが期限切れでないか

**解決方法:**
- Railwayログで`GMAIL_CREDENTIALS_JSON`や`CALENDAR_TOKEN_JSON`が読み込まれているか確認
- エラーメッセージで"OAuth"や"token expired"がないか確認

### 環境変数の確認方法

Railwayダッシュボードで「Variables」タブを開き、以下を確認：
- すべての変数が設定されている
- JSON変数の値が1行で入力されている
- シングルクォートで囲まれている

## 📚 参考ドキュメント

- [Railway環境変数ドキュメント](https://docs.railway.app/guides/variables)
- [Gmail API認証ガイド](https://developers.google.com/gmail/api/guides/auth)
- [Google Calendar API認証ガイド](https://developers.google.com/calendar/api/guides/auth)

---

**🎉 これでRailwayでVoiceAgentのフル機能が利用可能になります！**
