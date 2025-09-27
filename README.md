# 音声AIエージェント

ユーザーの音声指示を理解し、適切なツールを使って生活をサポートするインテリジェント音声エージェント

## ✨ 特徴

- **リアルタイム音声対話**: WebSocketベースの低遅延音声処理
- **AI+ルールベース応答**: 高速ルール処理とAIのハイブリッド応答システム
- **ハイブリッドLLM**: Claude API + OpenAI のマルチプロバイダー対応
- **個人情報管理**: ユーザー情報を記憶してパーソナライズ応答
- **高品質音声合成**: OpenAI TTSによる自然な日本語音声
- **モダンUI**: シンプルで洗練されたモノクロームデザイン
- **拡張可能なツールシステム**: モジュラー設計で機能追加が簡単

## 🏗️ アーキテクチャ

```
音声入力 → STT → ルールチェック → エージェントコア → ツール実行 → 応答生成 → TTS → 音声出力
              ↓       ↓              ↓                    ↓
    個人情報DB   AI処理        ツールレジストリ      履歴管理
```

## 🚀 セットアップ

### 1. 依存関係のインストール

```bash
# Python仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# パッケージのインストール
pip install -r requirements.txt
```

### 2. 環境設定

```bash
# 設定ファイルをコピー
cp .env.example .env

# .envファイルを編集してAPIキーを設定
```

### 3. サーバーの起動

```bash
# 開発サーバー起動
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 🎯 使用方法

1. ブラウザで `http://localhost:8000` を開く
2. マイクの使用を許可
3. 「話しかけてね」が表示されたらマイクボタンを押して話しかける
4. 個人情報を設定画面で登録（より個人に合った応答のため）
5. AIエージェントが応答し、必要に応じてツールを実行

### 音声コマンド例

**ルールベース処理（高速応答）:**
- "おはよう" → 挨拶応答
- "今何時？" → 現在時刻
- "今日の日付は？" → 現在日付
- "10 + 5" → 計算結果
- "ありがとう" → "どういたしまして。ではまた後ほど。"

**AI処理:**
- "今日の天気を教えて"
- "明日の予定をメモして"
- "プログラミングについて説明して"

## 📁 プロジェクト構造

```
voiceagent/
├── src/
│   ├── core/           # コアシステム（エージェント、ルール処理）
│   ├── audio/          # 音声処理（STT、TTS）
│   ├── llm/            # LLMインターフェース（Claude、OpenAI）
│   ├── memory/         # 記憶・学習システム
│   ├── tools/          # ツール実装（天気、計算、検索等）
│   └── main.py         # メインアプリケーション
├── templates/          # HTMLテンプレート
├── static/             # フロントエンド（CSS、JS）
├── data/               # データ保存（音声、メモリ）
└── tests/              # テスト
```

## 🔧 カスタマイズ

### 新しいツールの追加

`src/tools/` にツールクラスを追加：

```python
from src.core.tool_base import Tool

class WeatherTool(Tool):
    name = "weather"
    description = "天気情報を取得"

    async def execute(self, params: dict) -> str:
        # 実装
        return result
```

### ルールの追加

`src/core/rule_processor.py`にルールを追加：

```python
{
    "name": "custom_rule",
    "patterns": [r"カスタム.*パターン"],
    "responses": ["カスタム応答"],
    "priority": 10
}
```

## 🚀 デプロイ

### Vercel（推奨）

クラウドでの簡単デプロイ：

1. **環境変数の設定**
   ```bash
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

2. **デプロイ実行**
   ```bash
   # GitHubリポジトリをVercelに接続
   # 自動デプロイが開始されます
   ```

3. **利用可能な機能**
   - ✅ REST API チャット
   - ✅ LLM対話（Claude、OpenAI）
   - ✅ 基本ツール機能
   - ❌ WebSocket音声（サーバーレス制限）

📚 **詳細**: [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md) を参照

### Docker Compose

ローカル・VPS デプロイ：

```yaml
# docker-compose.yml
version: '3.8'
services:
  voiceagent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
```

## 📊 モニタリング

- ログ: `data/voiceagent.log`
- ダッシュボード: `http://localhost:8000/dashboard`
- API文書: `http://localhost:8000/docs`

## 🤝 コントリビュート

1. フォーク
2. フィーチャーブランチ作成
3. コミット
4. プルリクエスト

## 📄 ライセンス

MIT License