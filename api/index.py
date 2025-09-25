"""
Voice AI Agent - Vercel用エントリーポイント

サーバーレス環境での軽量版FastAPIアプリケーション
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 環境変数の読み込み
load_dotenv()

# Vercelでは一部のモジュールが利用できない可能性があるため、try-catch で囲む
try:
    from src.llm.hybrid_llm import HybridLLM
    from src.tools.tool_registry import ToolRegistry
    from src.memory.personal_memory import PersonalMemory
    from src.core.context_manager import ContextManager
    LLM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: LLM modules not available: {e}")
    LLM_AVAILABLE = False

# FastAPIアプリケーション作成（サーバーレス用）
app = FastAPI(
    title="Voice AI Agent API",
    description="インテリジェント音声エージェント API",
    version="1.0.0",
)

# 静的ファイルとテンプレートの設定
static_path = project_root / "static"
templates_path = project_root / "templates"

if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
if templates_path.exists():
    templates = Jinja2Templates(directory=str(templates_path))

# リクエスト/レスポンスモデル
class ChatRequest(BaseModel):
    message: str
    context: Optional[List[Dict[str, str]]] = []
    use_tools: Optional[bool] = True

class ChatResponse(BaseModel):
    response: str
    tool_calls: Optional[List[Dict[str, Any]]] = []
    status: str = "success"

class HealthResponse(BaseModel):
    status: str
    message: str
    available_features: List[str]

# グローバル変数（サーバーレスでは毎回初期化される）
_llm_instance = None
_tools_instance = None
_memory_instance = None
_context_instance = None

async def get_llm():
    """LLMインスタンスを取得（遅延初期化）"""
    global _llm_instance
    if _llm_instance is None and LLM_AVAILABLE:
        try:
            _llm_instance = HybridLLM()
            await _llm_instance.initialize()
        except Exception as e:
            print(f"LLM initialization failed: {e}")
    return _llm_instance

async def get_tools():
    """ツールインスタンスを取得（遅延初期化）"""
    global _tools_instance
    if _tools_instance is None and LLM_AVAILABLE:
        try:
            _tools_instance = ToolRegistry()
            await _tools_instance.initialize()
        except Exception as e:
            print(f"Tools initialization failed: {e}")
    return _tools_instance

async def get_memory():
    """メモリインスタンスを取得（遅延初期化）"""
    global _memory_instance
    if _memory_instance is None and LLM_AVAILABLE:
        try:
            _memory_instance = PersonalMemory()
            await _memory_instance.initialize()
        except Exception as e:
            print(f"Memory initialization failed: {e}")
    return _memory_instance

async def get_context():
    """コンテキストインスタンスを取得（遅延初期化）"""
    global _context_instance
    if _context_instance is None and LLM_AVAILABLE:
        try:
            _context_instance = ContextManager()
            await _context_instance.initialize()
        except Exception as e:
            print(f"Context initialization failed: {e}")
    return _context_instance

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ホームページ"""
    if templates_path.exists():
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return HTMLResponse("""
        <html>
        <head><title>Voice AI Agent</title></head>
        <body>
        <h1>Voice AI Agent</h1>
        <p>API is running! Visit <a href="/docs">/docs</a> for API documentation.</p>
        </body>
        </html>
        """)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェック"""
    features = ["REST API"]

    if LLM_AVAILABLE:
        features.extend(["LLM", "Tools", "Memory", "Context"])

    return HealthResponse(
        status="healthy",
        message="Voice AI Agent API is running on Vercel",
        available_features=features
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """チャット API エンドポイント"""
    try:
        if not LLM_AVAILABLE:
            return ChatResponse(
                response="申し訳ございませんが、現在LLM機能は利用できません。基本的なAPI機能のみ利用可能です。",
                status="limited"
            )

        # インスタンスを取得
        llm = await get_llm()
        tools = await get_tools()
        memory = await get_memory()
        context = await get_context()

        if not llm:
            return ChatResponse(
                response="LLMシステムの初期化に失敗しました。",
                status="error"
            )

        # コンテキストに追加
        if context:
            await context.add_user_message(request.message)

        # 関連記憶を検索
        relevant_memories = []
        if memory:
            try:
                relevant_memories = await memory.search_relevant(request.message, limit=3)
            except Exception as e:
                print(f"Memory search failed: {e}")

        # 利用可能なツール
        available_tools = []
        if tools and request.use_tools:
            try:
                available_tools = tools.get_available_tools()
            except Exception as e:
                print(f"Tools retrieval failed: {e}")

        # LLMで処理
        context_messages = request.context
        if context and not context_messages:
            try:
                context_messages = context.get_recent_context(5)
            except Exception as e:
                print(f"Context retrieval failed: {e}")

        response = await llm.process_with_tools(
            text=request.message,
            context=context_messages,
            memories=relevant_memories,
            available_tools=available_tools
        )

        response_text = response.get('response', '申し訳ございませんが、応答を生成できませんでした。')
        tool_calls = response.get('tool_calls', [])

        # 応答をコンテキストに追加
        if context:
            await context.add_assistant_message(response_text)

        # 会話を記憶に保存
        if memory:
            try:
                await memory.store_interaction(request.message, response_text)
            except Exception as e:
                print(f"Memory storage failed: {e}")

        return ChatResponse(
            response=response_text,
            tool_calls=tool_calls,
            status="success"
        )

    except Exception as e:
        print(f"Chat endpoint error: {e}")
        return ChatResponse(
            response=f"エラーが発生しました: {str(e)}",
            status="error"
        )

@app.get("/api/status")
async def status_endpoint():
    """システム状態確認"""
    status = {
        "api": "running",
        "llm_available": LLM_AVAILABLE,
        "features": {}
    }

    if not LLM_AVAILABLE:
        return status

    try:
        # 各コンポーネントの状態確認
        llm = await get_llm()
        if llm:
            llm_status = await llm.get_status()
            status["features"]["llm"] = llm_status

        tools = await get_tools()
        if tools:
            available_tools = tools.get_available_tools()
            status["features"]["tools"] = {
                "count": len(available_tools),
                "available": [tool["name"] for tool in available_tools]
            }

        memory = await get_memory()
        if memory:
            memory_status = await memory.get_status()
            status["features"]["memory"] = memory_status

    except Exception as e:
        status["error"] = str(e)

    return status

@app.get("/api/tools")
async def list_tools():
    """利用可能なツール一覧"""
    if not LLM_AVAILABLE:
        return {"tools": [], "message": "Tools not available"}

    try:
        tools = await get_tools()
        if tools:
            available_tools = tools.get_available_tools()
            return {"tools": available_tools}
        else:
            return {"tools": [], "message": "Tools initialization failed"}
    except Exception as e:
        return {"tools": [], "error": str(e)}

# デバッグ用エンドポイント
@app.get("/api/debug")
async def debug_info():
    """デバッグ情報"""
    return {
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "project_root": str(project_root),
        "environment_variables": {
            "OPENAI_API_KEY": "SET" if os.getenv("OPENAI_API_KEY") else "NOT SET",
            "ANTHROPIC_API_KEY": "SET" if os.getenv("ANTHROPIC_API_KEY") else "NOT SET",
            "PYTHONPATH": os.getenv("PYTHONPATH", "NOT SET")
        },
        "llm_available": LLM_AVAILABLE,
        "static_path_exists": static_path.exists(),
        "templates_path_exists": templates_path.exists()
    }

# Vercel用のハンドラー
def handler(request, response):
    """Vercel用のハンドラー関数"""
    return app

# 互換性のため
application = app