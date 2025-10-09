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
from src.core.tool_base import ToolResult
from src.api.gmail_auth import router as gmail_auth_router

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
# 起動時にデータディレクトリが存在しないとStaticFilesのマウントで落ちるため、先に作成しておく
os.makedirs("data/audio", exist_ok=True)
os.makedirs("data/memory", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")
templates = Jinja2Templates(directory="templates")

# APIルーターを登録
app.include_router(gmail_auth_router)


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

    # ステータスコールバックを設定
    async def send_status(message: str):
        await websocket.send_json({"type": "status", "message": message})

    app.state.voice_agent.status_callback = send_status

    try:
        while True:
            # 音声データの受信
            data = await websocket.receive_bytes()
            logger.debug(f"Received audio data: {len(data)} bytes")

            # 音声エージェントで処理
            response = await app.state.voice_agent.process_audio(data)

            # 応答の送信（音声認識結果とAI応答を分けて送信）
            if response:
                # 音声認識結果をチャット欄に表示
                if response.get("user_text"):
                    user_message = {
                        "type": "user_message",
                        "content": response.get("user_text"),
                        "timestamp": response.get("timestamp")
                    }
                    logger.info(f"🎤 Sending user_message to WebSocket: {user_message}")
                    await websocket.send_json(user_message)

                # AI応答をチャット欄に表示
                if response.get("text"):
                    assistant_message = {
                        "type": "assistant_message",
                        "content": response.get("text"),
                        "audio_url": response.get("audio_url"),
                        "timestamp": response.get("timestamp")
                    }
                    logger.info(f"🤖 Sending assistant_message to WebSocket: {assistant_message}")
                    await websocket.send_json(assistant_message)

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

            msg_type = message.get("type")

            # テキストメッセージ（互換: type='message' か 'text'）
            if msg_type in ("message", "text"):
                text_payload = message.get("message") or message.get("content") or ""
                response = await app.state.voice_agent.process_text(text_payload)

                await websocket.send_json({
                    "type": "response",
                    "content": response.get("text", ""),
                    "audio_url": response.get("audio_url")
                })

            # 設定更新
            elif msg_type == "config_update":
                cfg = message.get("config", {}) or {}

                # 既存の構成と整合する形に変換
                llm_updates = {}
                tts_updates = {}

                if "llm_provider" in cfg:
                    llm_updates["primary_provider"] = cfg["llm_provider"]
                if "tts_provider" in cfg:
                    tts_updates["provider"] = cfg["tts_provider"]

                updates = {}
                if llm_updates:
                    updates["llm"] = llm_updates
                if tts_updates:
                    updates["tts"] = tts_updates

                if updates:
                    await app.state.voice_agent.update_config(updates)

                await websocket.send_json({
                    "type": "status",
                    "status": "configured",
                    "applied": updates
                })

            # 会話リセット
            elif msg_type == "reset":
                try:
                    await app.state.voice_agent.context.reset_context()
                    await websocket.send_json({
                        "type": "status",
                        "status": "reset_done"
                    })
                except Exception as e:
                    logger.error(f"Failed to reset context: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "コンテキストのリセットに失敗しました"
                    })

            # 個人情報保存
            elif msg_type == "save_personal_info":
                personal_info = message.get("personal_info", {})
                try:
                    # メモリツール経由で個人情報を保存
                    memory_tool = app.state.voice_agent.tools.get_tool("memory")
                    if memory_tool:
                        await memory_tool.store_personal_info(personal_info)
                    else:
                        raise Exception("Memory tool not found")
                    await websocket.send_json({
                        "type": "status",
                        "status": "personal_info_saved",
                        "message": "個人情報を保存しました"
                    })
                    logger.info(f"Personal information saved: {personal_info}")
                except Exception as e:
                    logger.error(f"Failed to save personal information: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "個人情報の保存に失敗しました"
                    })

            # ステータス要求
            elif msg_type == "status_request":
                status = await app.state.voice_agent.get_status()
                await websocket.send_json({
                    "type": "status",
                    "status": status
                })

            else:
                logger.warning(f"Unknown chat message type: {msg_type}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
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


@app.get("/api/personality")
async def get_personality_type():
    """性格タイプの取得"""
    try:
        memory_tool = app.state.voice_agent.tools.get_tool("memory")
        if not memory_tool:
            return {"error": "Memory tool not found"}

        personality_type = await memory_tool.analyze_personality_type()
        return personality_type
    except Exception as e:
        logger.error(f"Failed to get personality type: {e}")
        return {"error": str(e)}


@app.get("/api/llm/models")
async def get_available_models():
    """利用可能なLLMモデル一覧を取得"""
    return {
        "claude": [
            {"value": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet (最新)", "description": "最も高性能なモデル"},
            {"value": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku (高速)", "description": "高速で低コスト"},
            {"value": "claude-3-opus-20240229", "label": "Claude 3 Opus (高性能)", "description": "Claude 3の最高性能モデル"},
            {"value": "claude-3-sonnet-20240229", "label": "Claude 3 Sonnet (バランス)", "description": "性能とコストのバランス"},
            {"value": "claude-3-haiku-20240307", "label": "Claude 3 Haiku (高速・低コスト)", "description": "最も高速で低コスト"}
        ],
        "openai": [
            {"value": "gpt-4o", "label": "GPT-4o (最新・最速)", "description": "最新の高性能モデル"},
            {"value": "gpt-4o-mini", "label": "GPT-4o Mini (高速・低コスト)", "description": "GPT-4oの小型版"},
            {"value": "gpt-4-turbo", "label": "GPT-4 Turbo", "description": "GPT-4の高速版"},
            {"value": "gpt-4", "label": "GPT-4", "description": "標準のGPT-4"},
            {"value": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo", "description": "高速で低コスト"}
        ]
    }


@app.get("/api/llm/current")
async def get_current_llm_config():
    """現在のLLM設定を取得"""
    try:
        status = await app.state.voice_agent.llm.get_status()
        return {
            "provider": status.get("primary_provider"),
            "model": status.get("providers", {}).get(status.get("primary_provider"), {}).get("model"),
            "available_providers": [p for p, info in status.get("providers", {}).items() if info.get("available")]
        }
    except Exception as e:
        logger.error(f"Failed to get current LLM config: {e}")
        return {"error": str(e)}


@app.post("/api/llm/switch")
async def switch_llm_model(request: dict):
    """LLMモデルを切り替え"""
    try:
        provider = request.get("provider")
        model = request.get("model")

        if not provider or not model:
            return {"error": "Provider and model are required"}

        # LLM設定を更新
        config = {
            "primary_provider": provider,
            "model": model
        }

        await app.state.voice_agent.llm.update_config(config)

        logger.info(f"LLM switched to {provider}/{model}")

        return {
            "success": True,
            "provider": provider,
            "model": model,
            "message": f"{provider}の{model}に切り替えました"
        }

    except Exception as e:
        logger.error(f"Failed to switch LLM model: {e}")
        return {"error": str(e)}


@app.get("/api/tools")
async def get_available_tools():
    """利用可能なツール一覧を取得"""
    try:
        tools = app.state.voice_agent.tools.get_available_tools()
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Failed to get tools: {e}")
        return {"error": str(e)}


@app.get("/api/voice/current")
async def get_current_voice():
    """現在のボイス設定を取得"""
    try:
        voice = app.state.voice_agent.tts.config.get("voice", "alloy")
        return {
            "voice": voice
        }
    except Exception as e:
        logger.error(f"Failed to get current voice: {e}")
        return {"error": str(e)}


@app.post("/api/voice/switch")
async def switch_voice(request: dict):
    """ボイスを切り替え"""
    try:
        voice = request.get("voice")

        if not voice:
            return {"error": "Voice is required"}

        # ボイス設定を更新
        app.state.voice_agent.tts.config["voice"] = voice

        logger.info(f"Voice switched to {voice}")

        return {
            "success": True,
            "voice": voice,
            "message": f"{voice}に切り替えました"
        }

    except Exception as e:
        logger.error(f"Failed to switch voice: {e}")
        return {"error": str(e)}


@app.get("/api/mode/current")
async def get_current_mode():
    """現在のAIモード設定を取得"""
    try:
        # メモリツールから現在のモードを取得
        memory_tool = app.state.voice_agent.tools.get_tool("memory")
        if memory_tool:
            mode = await memory_tool.get_ai_mode()
            return {"mode": mode or "assist"}  # デフォルトはアシストモード
        return {"mode": "assist"}
    except Exception as e:
        logger.error(f"Failed to get current mode: {e}")
        return {"mode": "assist", "error": str(e)}


@app.post("/api/mode/switch")
async def switch_mode(request: dict):
    """AIモードを切り替え"""
    try:
        mode = request.get("mode")

        if not mode or mode not in ["assist", "auto"]:
            return {"error": "Valid mode is required (assist, auto)"}

        # メモリツールにモードを保存
        memory_tool = app.state.voice_agent.tools.get_tool("memory")
        if memory_tool:
            await memory_tool.set_ai_mode(mode)

        logger.info(f"AI mode switched to {mode}")

        mode_names = {
            "assist": "アシストモード",
            "auto": "全自動モード"
        }

        return {
            "success": True,
            "mode": mode,
            "message": f"{mode_names[mode]}に切り替えました"
        }

    except Exception as e:
        logger.error(f"Failed to switch mode: {e}")
        return {"error": str(e)}


@app.post("/api/tts")
async def text_to_speech(request: dict):
    """テキストを音声に変換"""
    try:
        text = request.get("text")

        if not text:
            return {"error": "Text is required"}

        # TTSで音声生成
        audio_data = await app.state.voice_agent.tts.synthesize(text)

        # Base64エンコード
        import base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return {
            "success": True,
            "audio": audio_base64
        }

    except Exception as e:
        logger.error(f"Failed to synthesize speech: {e}")
        return {"error": str(e)}


@app.post("/api/alarms/set")
async def set_alarm(request: dict):
    """アラームを設定"""
    try:
        alarm_tool = app.state.voice_agent.tools.get_tool("alarm")
        if not alarm_tool:
            return {"error": "Alarm tool not available"}

        result = await alarm_tool.execute({
            "action": "set",
            "time": request.get("time"),
            "label": request.get("label", "アラーム"),
            "message": request.get("message", ""),
            "repeat": request.get("repeat", False)
        })

        if isinstance(result, ToolResult):
            if result.success:
                return {
                    "success": True,
                    "alarm": result.result.get("alarm"),
                    "message": result.result.get("message")
                }
            else:
                return {"error": result.error}

        return {"error": "Unexpected response from alarm tool"}

    except Exception as e:
        logger.error(f"Failed to set alarm: {e}")
        return {"error": str(e)}


@app.get("/api/alarms/list")
async def list_alarms():
    """アラーム一覧を取得"""
    try:
        alarm_tool = app.state.voice_agent.tools.get_tool("alarm")
        if not alarm_tool:
            return {"error": "Alarm tool not available"}

        result = await alarm_tool.execute({"action": "list"})

        if isinstance(result, ToolResult):
            if result.success:
                return {
                    "success": True,
                    "alarms": result.result.get("alarms", []),
                    "count": result.result.get("count", 0)
                }
            else:
                return {"error": result.error}

        return {"error": "Unexpected response from alarm tool"}

    except Exception as e:
        logger.error(f"Failed to list alarms: {e}")
        return {"error": str(e)}


@app.post("/api/alarms/delete")
async def delete_alarm(request: dict):
    """アラームを削除"""
    try:
        alarm_tool = app.state.voice_agent.tools.get_tool("alarm")
        if not alarm_tool:
            return {"error": "Alarm tool not available"}

        result = await alarm_tool.execute({
            "action": "delete",
            "alarm_id": request.get("alarm_id")
        })

        if isinstance(result, ToolResult):
            if result.success:
                return {
                    "success": True,
                    "message": result.result.get("message")
                }
            else:
                return {"error": result.error}

        return {"error": "Unexpected response from alarm tool"}

    except Exception as e:
        logger.error(f"Failed to delete alarm: {e}")
        return {"error": str(e)}


@app.get("/api/table/tasks")
async def get_table_tasks():
    """テーブルタスク一覧を取得"""
    try:
        memory_tool = app.state.voice_agent.tools.get_tool("memory")
        if not memory_tool:
            return {"success": False, "error": "Memory tool not available", "tasks": []}

        tasks = await memory_tool.get_table_tasks()
        return {
            "success": True,
            "tasks": tasks
        }

    except Exception as e:
        logger.error(f"Failed to get table tasks: {e}")
        return {"success": False, "error": str(e), "tasks": []}


@app.post("/api/table/tasks/add")
async def add_table_task(request: dict):
    """テーブルタスクを追加"""
    try:
        memory_tool = app.state.voice_agent.tools.get_tool("memory")
        if not memory_tool:
            return {"success": False, "error": "Memory tool not available"}

        task = await memory_tool.add_table_task(
            title=request.get("title"),
            content=request.get("content"),
            status=request.get("status", "processing")
        )

        return {
            "success": True,
            "task": task
        }

    except Exception as e:
        logger.error(f"Failed to add table task: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/table/tasks/update")
async def update_table_task(request: dict):
    """テーブルタスクを更新"""
    try:
        memory_tool = app.state.voice_agent.tools.get_tool("memory")
        if not memory_tool:
            return {"success": False, "error": "Memory tool not available"}

        await memory_tool.update_table_task(
            task_id=request.get("task_id"),
            status=request.get("status"),
            result=request.get("result", "")
        )

        return {
            "success": True
        }

    except Exception as e:
        logger.error(f"Failed to update table task: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/alarms/trigger")
async def trigger_alarm(request: dict):
    """アラームを発動してAIエージェントに読み上げさせる"""
    try:
        message = request.get("message", "アラームの時間です")

        # TTSで音声生成（ファイルパスが返される）
        audio_path = await app.state.voice_agent.tts.synthesize(message)

        if not audio_path:
            raise Exception("TTS synthesis failed - no audio path returned")

        # ファイルパスから実際のファイルパスに変換（/data/xxx -> ./data/xxx）
        if audio_path.startswith("/data/"):
            actual_path = "." + audio_path
        else:
            actual_path = audio_path

        # ファイルを読み込んでBase64エンコード
        import base64
        with open(actual_path, 'rb') as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        return {
            "success": True,
            "audio": audio_base64,
            "text": message
        }

    except Exception as e:
        logger.error(f"Failed to trigger alarm: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/gmail/info")
async def get_gmail_info():
    """Gmail連携情報を取得"""
    try:
        gmail_tool = app.state.voice_agent.tools.get_tool("gmail")
        if not gmail_tool:
            return {"connected": False, "error": "Gmail tool not available"}

        # まだ認証されていない場合は認証を試みる
        if not gmail_tool.service:
            await gmail_tool._authenticate()

        # GmailツールのAPIクライアントから認証情報を取得
        if hasattr(gmail_tool, 'service') and gmail_tool.service:
            # 認証済みの場合、ユーザー情報を取得
            try:
                # Gmail APIでユーザープロフィールを取得
                profile = gmail_tool.service.users().getProfile(userId='me').execute()
                email_address = profile.get('emailAddress')

                return {
                    "connected": True,
                    "email": email_address
                }
            except Exception as e:
                logger.error(f"Failed to get Gmail profile: {e}")
                return {"connected": False, "error": "Failed to get email address"}
        else:
            return {"connected": False, "error": "Gmail not authenticated"}

    except Exception as e:
        logger.error(f"Failed to get Gmail info: {e}")
        return {"connected": False, "error": str(e)}


@app.get("/api/calendar/info")
async def get_calendar_info():
    """カレンダー連携情報を取得"""
    try:
        calendar_tool = app.state.voice_agent.tools.get_tool("calendar")
        if not calendar_tool:
            return {"connected": False, "error": "Calendar tool not available"}

        # 認証情報が存在するか確認
        if hasattr(calendar_tool, 'service') and calendar_tool.service:
            try:
                # トークンファイルから情報を読み取る
                import json
                import os
                token_file = "./mcp_servers/calendar-mcp/.gcp-saved-tokens.json"

                email = "連携済み"
                if os.path.exists(token_file):
                    with open(token_file, 'r') as f:
                        token_data = json.load(f)
                        email = token_data.get("account", email)

                # カレンダー一覧を取得
                calendar_list = calendar_tool.service.calendarList().list().execute()
                calendars = [cal.get('summary', 'Unnamed') for cal in calendar_list.get('items', [])]

                return {
                    "connected": True,
                    "email": email,
                    "calendars": calendars[:5]  # 最初の5個まで
                }
            except Exception as e:
                logger.error(f"Failed to get Calendar info: {e}")
                return {"connected": False, "error": "Failed to get calendar info"}
        else:
            return {"connected": False, "error": "Calendar not authenticated"}

    except Exception as e:
        logger.error(f"Error getting Calendar info: {e}")
        return {"connected": False, "error": str(e)}


@app.post("/api/vision/analyze")
async def analyze_vision(request: Request):
    """画像を分析"""
    try:
        data = await request.json()
        image = data.get("image")
        query = data.get("query", "この画像について詳しく教えてください")

        if not image:
            return {"success": False, "error": "画像データが必要です"}

        # Visionツールを取得
        vision_tool = app.state.voice_agent.tools.get_tool("vision")
        if not vision_tool:
            return {"success": False, "error": "Vision tool not available"}

        # 画像分析を実行
        result = await vision_tool.execute({
            "image": image,
            "query": query
        })

        # ToolResultの場合は結果を抽出
        if isinstance(result, ToolResult):
            analysis_text = result.result
            success = result.success
        else:
            analysis_text = str(result)
            success = True

        # TTS音声合成
        audio_url = await app.state.voice_agent.tts.synthesize(analysis_text)

        return {
            "success": success,
            "result": analysis_text,
            "audio_url": audio_url
        }

    except Exception as e:
        logger.error(f"Failed to analyze vision: {e}")
        return {"success": False, "error": str(e)}


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
