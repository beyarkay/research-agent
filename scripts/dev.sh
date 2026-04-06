#!/usr/bin/env bash
# Start both backend and frontend dev servers
set -euo pipefail

cd "$(dirname "$0")/.."

# Build frontend first
echo "Building frontend..."
(cd frontend && npx vite build)

echo ""
echo "Starting server at http://127.0.0.1:8000"
echo "Press Ctrl+C to stop"
echo ""

cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
