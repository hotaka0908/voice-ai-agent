"""
Session Dependencies for FastAPI

FastAPIのエンドポイントでセッションIDを取得・検証する依存性
"""

from fastapi import Header, HTTPException
from src.middleware.session import session_manager
from typing import Optional
from loguru import logger


async def get_session_id(x_session_id: Optional[str] = Header(None)) -> str:
    """
    セッションIDを取得・検証する依存性

    Args:
        x_session_id: HTTPヘッダーから取得したセッションID

    Returns:
        str: 検証済みのセッションID

    Raises:
        HTTPException: セッションIDが無効な場合

    使用例:
        @app.get("/api/example")
        async def example(session_id: str = Depends(get_session_id)):
            # session_idを使用
            pass
    """
    if not x_session_id:
        logger.warning("Session ID not provided in request headers")
        raise HTTPException(
            status_code=400,
            detail="Session ID is required. Please include 'X-Session-ID' header."
        )

    if not session_manager.validate_session_id(x_session_id):
        logger.error(f"Invalid session ID format: {x_session_id}")
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID format. Session ID must be a valid UUID v4."
        )

    logger.debug(f"Session ID validated: {x_session_id}")
    return x_session_id


async def get_optional_session_id(x_session_id: Optional[str] = Header(None)) -> Optional[str]:
    """
    セッションIDを取得（オプション）

    セッションIDがない場合でもエラーにしない
    環境変数からのフォールバック用

    Args:
        x_session_id: HTTPヘッダーから取得したセッションID

    Returns:
        Optional[str]: セッションID（存在する場合）、None（存在しない場合）
    """
    if not x_session_id:
        return None

    if not session_manager.validate_session_id(x_session_id):
        logger.warning(f"Invalid session ID format (optional): {x_session_id}")
        return None

    return x_session_id
