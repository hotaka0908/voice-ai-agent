# Railway Deployment Dockerfile
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /app

# システム依存パッケージをインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# データディレクトリを作成
RUN mkdir -p data/audio data/memory

# 起動スクリプトに実行権限を付与
RUN chmod +x start.sh

# ポートを公開
EXPOSE 8000

# アプリケーション起動
CMD ["./start.sh"]
