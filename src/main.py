"""
Voice AI Agent - メインアプリケーション

リアルタイム音声対話システムのメインエントリーポイント
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from loguru import logger
from dotenv import load_dotenv

from src.core.agent import VoiceAgent
from src.core.websocket_manager import WebSocketManager

# 環境変数の読み込み
load_dotenv()

# ログ設定
logger.add(
    os.getenv("LOG_FILE", "./data/voiceagent.log"),
    rotation="1 day",
    retention="30 days",
    level=os.getenv("LOG_LEVEL", "INFO")
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    logger.info("Voice AI Agent starting up...")

    # グローバルインスタンスの初期化
    app.state.voice_agent = VoiceAgent()
    app.state.websocket_manager = WebSocketManager()

    # 初期化処理
    await app.state.voice_agent.initialize()
    logger.info("Voice AI Agent ready!")

    yield

    # クリーンアップ処理
    logger.info("Voice AI Agent shutting down...")
    await app.state.voice_agent.cleanup()


# FastAPIアプリケーションの作成
app = FastAPI(
    title="Voice AI Agent",
    description="インテリジェント音声エージェント",
    version="1.0.0",
    lifespan=lifespan
)

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ホームページ"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy", "message": "Voice AI Agent is running"}


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """音声通信用WebSocketエンドポイント"""
    await app.state.websocket_manager.connect(websocket)

    try:
        while True:
            # 音声データの受信
            data = await websocket.receive_bytes()
            logger.debug(f"Received audio data: {len(data)} bytes")

            # 音声エージェントで処理
            response = await app.state.voice_agent.process_audio(data)

            # 応答の送信
            if response:
                await websocket.send_json({
                    "type": "response",
                    "data": response
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        app.state.websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        app.state.websocket_manager.disconnect(websocket)


@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """チャット用WebSocketエンドポイント"""
    await app.state.websocket_manager.connect(websocket)

    try:
        while True:
            # テキストメッセージの受信
            message = await websocket.receive_json()
            logger.debug(f"Received chat message: {message}")

            # テキスト処理
            if message.get("type") == "text":
                response = await app.state.voice_agent.process_text(
                    message.get("content", "")
                )

                # 応答の送信
                await websocket.send_json({
                    "type": "response",
                    "content": response.get("text", ""),
                    "audio_url": response.get("audio_url")
                })

    except WebSocketDisconnect:
        logger.info("Chat WebSocket disconnected")
        app.state.websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Chat WebSocket error: {e}")
        app.state.websocket_manager.disconnect(websocket)


@app.get("/api/status")
async def get_status():
    """システム状態の取得"""
    return await app.state.voice_agent.get_status()


@app.post("/api/configure")
async def configure_agent(config: dict):
    """エージェントの設定変更"""
    await app.state.voice_agent.update_config(config)
    return {"status": "configured"}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "true").lower() == "true"

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )