#!/usr/bin/env bash
# One-command local startup for both backend and frontend
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Port helpers ─────────────────────────────────────────────────────────────

free_port() {
  local port=$1
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null) || true
  if [ -n "$pids" ]; then
    echo "  Port $port in use (PIDs: $pids) — releasing..."
    echo "$pids" | xargs kill -TERM 2>/dev/null || true
    # Give processes up to 3 seconds to exit gracefully, then force-kill
    local i=0
    while [ $i -lt 6 ]; do
      sleep 0.5
      pids=$(lsof -ti :"$port" 2>/dev/null) || true
      [ -z "$pids" ] && break
      i=$((i + 1))
    done
    pids=$(lsof -ti :"$port" 2>/dev/null) || true
    if [ -n "$pids" ]; then
      echo "  Force-killing remaining PIDs on port $port: $pids"
      echo "$pids" | xargs kill -KILL 2>/dev/null || true
      sleep 0.5
    fi
    echo "  Port $port is now free."
  fi
}

# ── Backend ──────────────────────────────────────────────────────────────────
echo "→ Starting backend on http://localhost:8100"
cd "$ROOT"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "  Created .env from .env.example — fill in your API keys"
fi

if [ ! -d ".venv" ]; then
  echo "  Creating Python venv..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -e ".[dev]" -q

free_port 8100
uvicorn backend.main:app --host 0.0.0.0 --port 8100 --reload &
BACKEND_PID=$!

# ── Frontend ─────────────────────────────────────────────────────────────────
echo "→ Starting frontend on http://localhost:5173"
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  echo "  Installing npm packages..."
  npm install
fi

free_port 5173
npm run dev &
FRONTEND_PID=$!

# ── Cleanup on Ctrl+C ────────────────────────────────────────────────────────
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

echo ""
echo "✓ Backend:  http://localhost:8100"
echo "✓ Frontend: http://localhost:5173"
echo "✓ MCP SSE:  http://localhost:8100/mcp/sse"
echo ""
echo "Press Ctrl+C to stop both servers."
wait
