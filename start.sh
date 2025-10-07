#!/bin/bash
set -e

# デフォルトポートは8000
PORT=${PORT:-8000}

# uvicornを起動
exec uvicorn src.main:app --host 0.0.0.0 --port $PORT
