# Vercelデプロイメントガイド

## 概要

Voice AI AgentをVercelにデプロイするためのステップバイステップガイドです。

## 前提条件

- Vercel アカウント
- GitHub リポジトリがVercelに連携済み
- APIキー（OpenAI、Anthropic）

## デプロイ手順

### 1. リポジトリをVercelに接続

1. [Vercel ダッシュボード](https://vercel.com/dashboard) にログイン
2. "New Project" をクリック
3. GitHubリポジトリ `hotaka0908/voice-ai-agent` を選択
4. "Import" をクリック

### 2. 環境変数の設定

Vercelプロジェクトの設定画面で以下の環境変数を設定：

#### 必須環境変数
```
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

#### オプション環境変数
```
LOG_LEVEL=INFO
PRIMARY_LLM=claude
FALLBACK_LLM=openai
PRIVACY_MODE=false
```

### 3. 設定の確認

**Build Command**: 自動設定（空のまま）
**Output Directory**: 自動設定（空のまま）
**Install Command**: `pip install -r requirements.txt`

### 4. デプロイ実行

"Deploy" ボタンをクリックしてデプロイを開始。

## 利用可能な機能

### Vercelでサポートされる機能
✅ REST API (`/api/chat`)
✅ ヘルスチェック (`/health`)
✅ LLM対話（Claude、OpenAI）
✅ 基本的なツール機能
✅ モック記憶システム

### Vercelで制限される機能
❌ WebSocket（リアルタイム音声）
❌ 音声処理（Whisper、TTS）
❌ Vector Database（ChromaDB）
❌ ローカルファイルストレージ

## API エンドポイント

デプロイ後は以下のエンドポイントが利用可能：

- `GET /` - ホームページ
- `GET /health` - ヘルスチェック
- `POST /api/chat` - チャットAPI
- `GET /api/status` - システム状態
- `GET /api/tools` - 利用可能なツール一覧
- `GET /api/debug` - デバッグ情報

## チャットAPIの使用例

```bash
curl -X POST "https://your-vercel-app.vercel.app/api/chat" \\
     -H "Content-Type: application/json" \\
     -d '{
       "message": "こんにちは！今日の天気はどうですか？",
       "use_tools": true
     }'
```

## トラブルシューティング

### よくあるエラー

#### 1. ビルドエラー
```
Error: Could not install packages due to an EnvironmentError
```
**解決策**: requirements.txtが軽量版になっているか確認

#### 2. API キーエラー
```
LLM providers are not available
```
**解決策**: Vercelの環境変数設定を確認

#### 3. モジュール不足エラー
```
ModuleNotFoundError: No module named 'xxx'
```
**解決策**: requirements.txtに必要パッケージを追加

### ログ確認方法

1. Vercel ダッシュボード → プロジェクト選択
2. "Functions" タブ → 実行ログを確認
3. `/api/debug` エンドポイントでシステム情報を確認

## ローカル開発との違い

| 機能 | ローカル | Vercel |
|------|----------|---------|
| WebSocket | ✅ | ❌ |
| 音声処理 | ✅ | ❌ |
| Vector DB | ✅ | ❌（モック） |
| LLM対話 | ✅ | ✅ |
| REST API | ✅ | ✅ |

## セキュリティ注意事項

- APIキーは必ずVercelの環境変数で設定
- `.env`ファイルは`.gitignore`で除外されている
- 本番環境では適切なCORS設定を検討

## サポート

問題が発生した場合：
1. [Vercelドキュメント](https://vercel.com/docs) を確認
2. プロジェクトのIssuesに報告
3. `/api/debug` エンドポイントの情報を含める