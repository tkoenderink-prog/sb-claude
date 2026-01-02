#!/bin/bash
# Local development mode
# - Infrastructure (PostgreSQL, ChromaDB) runs in Docker
# - Backend and Frontend run locally with hot reload
# - Backend: localhost:8001, Frontend: localhost:3001

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Second Brain Local Development ==="
echo "Mode: LOCAL (backend:8001, frontend:3001)"
echo ""

# Start infrastructure if not running
if ! docker ps --format '{{.Names}}' | grep -q "second-brain-db"; then
    echo "Starting infrastructure..."
    docker compose -f docker-compose.infra.yml up -d

    echo "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker exec second-brain-db pg_isready -U secondbrain >/dev/null 2>&1; then
            echo "PostgreSQL ready!"
            break
        fi
        sleep 1
    done
else
    echo "Infrastructure already running."
fi

# Stop any Docker application containers (they use ports 3000/8000)
echo ""
echo "Stopping any Docker app containers..."
docker stop second-brain-backend second-brain-frontend second-brain-backend-dev second-brain-frontend-dev 2>/dev/null || true

# Kill any existing local servers on our ports
echo "Cleaning up existing processes..."
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
sleep 1

# Verify ports are free
if lsof -i:3001 -i:8001 >/dev/null 2>&1; then
    echo "ERROR: Ports 3001 or 8001 still in use."
    exit 1
fi

# Export environment for local dev
export DEV_MODE=local
export DEV_PORT=8001
export CHROMA_HOST=localhost
export CHROMA_PORT=8002

echo ""
echo "Starting backend on port 8001..."
cd "$PROJECT_ROOT/services/brain_runtime"
uv run uvicorn main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

echo "Waiting for backend..."
for i in {1..30}; do
    if curl -s http://localhost:8001/health >/dev/null 2>&1; then
        echo "Backend ready!"
        break
    fi
    sleep 1
done

echo ""
echo "Starting frontend on port 3001..."
cd "$PROJECT_ROOT/apps/web"
NEXT_PUBLIC_API_URL=http://localhost:8001 PORT=3001 pnpm dev &
FRONTEND_PID=$!

echo "Waiting for frontend..."
for i in {1..60}; do
    if curl -s http://localhost:3001 >/dev/null 2>&1; then
        echo "Frontend ready!"
        break
    fi
    sleep 2
done

echo ""
echo "==========================================="
echo "  LOCAL DEVELOPMENT MODE"
echo "==========================================="
echo ""
echo "  Frontend: http://localhost:3001"
echo "  Backend:  http://localhost:8001"
echo "  Health:   http://localhost:3001/health"
echo ""
echo "  Infrastructure (Docker):"
echo "    PostgreSQL: localhost:5432"
echo "    ChromaDB:   localhost:8002"
echo ""
echo "  Docker mode available on :3000/:8000"
echo "==========================================="
echo ""
echo "Press Ctrl+C to stop local servers"
echo "(Infrastructure keeps running in Docker)"

# Cleanup on exit
cleanup() {
    echo ""
    echo "Stopping local servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Local servers stopped. Infrastructure still running."
    echo "To stop infrastructure: ./scripts/infra-stop.sh"
}
trap cleanup EXIT

# Wait for either to exit
wait $BACKEND_PID $FRONTEND_PID
