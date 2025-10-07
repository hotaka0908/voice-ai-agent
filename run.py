#!/usr/bin/env python3
"""
Railway用起動スクリプト
環境変数PORTを読み取ってuvicornを起動
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
