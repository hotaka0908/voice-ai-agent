# 🎙️ Voice AI Agent

ユーザーの音声指示を理解し、適切なツールを使って生活をサポートするインテリジェント音声エージェント

## ✨ 特徴

- **リアルタイム音声対話**: WebSocketベースの低遅延音声処理
- **ハイブリッドLLM**: Claude API + ローカルOllama でプライバシーと性能を両立
- **パーソナル学習**: RAGとベクトルDBによる個人適応型AI
- **スマートホーム連携**: Home Assistantとの統合で家電制御
- **自然な音声合成**: ElevenLabsによる感情表現豊かなTTS
- **拡張可能なツールシステム**: モジュラー設計で機能追加が簡単

## 🏗️ アーキテクチャ

```
音声入力 → STT → NLU → エージェントコア → ツール実行 → 応答生成 → TTS → 音声出力
              ↓         ↓                    ↓
    パーソナルDB    ツールレジストリ      履歴管理
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

### 3. Ollamaのセットアップ（ローカルLLM用）

```bash
# Ollamaのインストール
curl -fsSL https://ollama.ai/install.sh | sh

# モデルのダウンロード
ollama pull llama3.2
```

### 4. データベースの初期化

```bash
# PostgreSQLの起動（DockerまたはローカルDB）
python -m alembic upgrade head
```

### 5. サーバーの起動

```bash
# 開発サーバー起動
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 🎯 使用方法

1. ブラウザで `http://localhost:8000` を開く
2. マイクの使用を許可
3. 「聞いています...」が表示されたら話しかける
4. AIエージェントが応答し、必要に応じてツールを実行

### 音声コマンド例

- "今日の天気を教えて"
- "リビングの電気をつけて"
- "明日の予定をメモして"
- "音楽をかけて"
- "部屋の温度を22度にして"

## 📁 プロジェクト構造

```
voiceagent/
├── src/
│   ├── core/           # コアシステム
│   ├── audio/          # 音声処理
│   ├── llm/            # LLMインターフェース
│   ├── memory/         # 記憶・学習システム
│   ├── tools/          # ツール実装
│   └── smart_home/     # スマートホーム連携
├── tests/              # テスト
├── data/               # データ保存
├── config/             # 設定ファイル
└── static/             # 静的ファイル
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

### 音声モデルのカスタマイズ

ElevenLabsで音声をクローンして、`.env`のVOICE_IDを変更

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