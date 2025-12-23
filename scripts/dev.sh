#!/bin/bash
# Development startup script - ensures clean server state

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Second Brain Development Server ==="
echo "Project: $PROJECT_ROOT"

# Kill any existing servers on our ports
echo "Cleaning up existing processes..."
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Verify ports are free
if lsof -i:3000 -i:8000 >/dev/null 2>&1; then
    echo "ERROR: Ports still in use. Please close other applications."
    exit 1
fi

echo "Starting backend on port 8000..."
cd "$PROJECT_ROOT/services/brain_runtime"
uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Waiting for backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "Backend ready!"
        break
    fi
    sleep 1
done

echo "Starting frontend on port 3000..."
cd "$PROJECT_ROOT/apps/web"
pnpm dev &
FRONTEND_PID=$!

echo "Waiting for frontend..."
for i in {1..60}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "Frontend ready!"
        break
    fi
    sleep 2
done

echo ""
echo "=== Servers Running ==="
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for either to exit
wait $BACKEND_PID $FRONTEND_PID
