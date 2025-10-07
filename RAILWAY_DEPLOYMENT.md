# Railway デプロイガイド

voiceagentをRailwayにデプロイする手順

## 📋 前提条件

- GitHubアカウント
- Railwayアカウント（https://railway.app/）
- APIキー（OpenAI、Anthropic）

## 🚀 デプロイ手順

### 1. Railwayプロジェクトを作成

1. [Railway](https://railway.app/)にアクセスしてログイン
2. 「New Project」をクリック
3. 「Deploy from GitHub repo」を選択
4. `voice-ai-agent`リポジトリを選択

### 2. 環境変数を設定

Railwayのダッシュボードで以下の環境変数を設定：

```bash
# 必須
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# オプション（デフォルト値あり）
DEFAULT_LLM_PROVIDER=claude
DEFAULT_VOICE=alloy
DEFAULT_AI_MODE=assist
LOG_LEVEL=INFO
```

### 3. Gmail API設定（オプション）

Gmail機能を使う場合：

1. Google Cloud Consoleで認証情報JSONをダウンロード
2. Railwayの「Variables」タブで以下を設定：
   ```bash
   GMAIL_CREDENTIALS_JSON='{"installed":{"client_id":"...","project_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_secret":"...","redirect_uris":["..."]}}''
   ```

3. 初回認証が必要なため、ローカルで`token.json`を生成してからRailwayにアップロード

### 4. デプロイ

Railwayは自動的にデプロイを開始します：

- ビルドログで進捗確認
- デプロイ完了後、公開URLが発行される（例: `https://your-app.railway.app`）

## 🔧 設定ファイル

プロジェクトには以下のファイルが含まれています：

- **railway.json**: Railway設定
- **nixpacks.toml**: ビルド設定（Python 3.10 + ffmpeg）
- **Procfile**: 起動コマンド
- **requirements.txt**: Python依存関係

## 📊 利用可能な機能

✅ **動作する機能:**
- リアルタイム音声対話（WebSocket）
- 処理状態表示
- Gmail連携（認証設定後）
- カレンダー連携（認証設定後）
- カメラ画像認識
- アラーム機能
- 性格タイプ分析
- 個人情報管理
- 全自動モード

## 🎯 デプロイ後の確認

1. **接続テスト**: ブラウザで公開URLにアクセス
2. **WebSocket確認**: 開発者ツールのコンソールで接続状態を確認
3. **音声テスト**: マイク許可後、音声入力をテスト
4. **ツールテスト**: Gmail、アラームなどの機能をテスト

## 💰 コスト

Railwayの料金プラン：

- **Hobby Plan**: $5/月（500時間の実行時間含む）
- **従量課金**: 使用リソースに応じて追加料金

音声AIエージェントは常時稼働するため、Hobby Planで十分です。

## 🔄 アップデート

GitHubリポジトリにpushすると、Railwayが自動的に再デプロイします：

```bash
git add .
git commit -m "Update feature"
git push
```

## ⚠️ 注意事項

1. **Gmail認証**: 初回認証はローカルで行う必要があります
2. **音声ファイル**: `data/audio/`ディレクトリは永続化されません（必要に応じてS3等を使用）
3. **メモリ制限**: 大量の同時接続がある場合はプラン変更が必要

## 🆘 トラブルシューティング

### デプロイが失敗する

- ログを確認: `railway logs`
- 環境変数が正しく設定されているか確認
- `requirements.txt`の依存関係を確認

### WebSocketが接続できない

- RailwayはWebSocketをサポートしているため、通常は問題なし
- ブラウザのコンソールでエラーメッセージを確認

### 音声が再生されない

- HTTPSで接続されているか確認（Railwayは自動的にHTTPS）
- ブラウザのマイク許可を確認
- OpenAI APIキーが正しく設定されているか確認

## 📚 参考リンク

- [Railway ドキュメント](https://docs.railway.app/)
- [Nixpacks ドキュメント](https://nixpacks.com/)
- [FastAPI デプロイガイド](https://fastapi.tiangolo.com/deployment/)
