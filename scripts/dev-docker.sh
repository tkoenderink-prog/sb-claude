#!/bin/bash
# Docker development mode with volume mounts
# - All services run in Docker
# - Source code mounted for hot reload
# - Backend: localhost:8000, Frontend: localhost:3000

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Second Brain Docker Development ==="
echo "Mode: DOCKER (backend:8000, frontend:3000)"
echo ""

# Kill any local dev servers (they use ports 3001/8001)
echo "Stopping any local dev servers..."
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true

# Check if we need to build
BUILD_FLAG=""
if [[ "$1" == "--build" ]] || [[ "$1" == "-b" ]]; then
    BUILD_FLAG="--build"
    echo "Building images..."
fi

# Check if dev images exist
if ! docker images | grep -q "second-brain-app-backend" || [[ -n "$BUILD_FLAG" ]]; then
    echo "Building development images..."
    BUILD_FLAG="--build"
fi

echo ""
echo "Starting Docker development environment..."
docker compose -f docker-compose.infra.yml -f docker-compose.dev.yml up $BUILD_FLAG -d

echo ""
echo "Waiting for services..."

# Wait for backend
for i in {1..60}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "Backend ready!"
        break
    fi
    sleep 2
done

# Wait for frontend
for i in {1..90}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "Frontend ready!"
        break
    fi
    sleep 2
done

echo ""
echo "==========================================="
echo "  DOCKER DEVELOPMENT MODE"
echo "==========================================="
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  Health:   http://localhost:3000/health"
echo ""
echo "  Source mounted - changes auto-reload"
echo ""
echo "  Commands:"
echo "    Logs:    docker compose -f docker-compose.infra.yml -f docker-compose.dev.yml logs -f"
echo "    Stop:    ./scripts/dev-docker-stop.sh"
echo "    Rebuild: ./scripts/dev-docker.sh --build"
echo ""
echo "  Local mode available on :3001/:8001"
echo "==========================================="
