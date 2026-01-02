#!/bin/bash
# Start infrastructure services only (PostgreSQL + ChromaDB)
# These run in Docker regardless of which development mode you use

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Second Brain Infrastructure ==="
echo ""

# Check if services are already running
if docker ps --format '{{.Names}}' | grep -q "second-brain-db"; then
    echo "Infrastructure already running."
    echo ""
    docker compose -f docker-compose.infra.yml ps
    echo ""
    echo "Services:"
    echo "  PostgreSQL: localhost:5432"
    echo "  ChromaDB:   localhost:8002"
    exit 0
fi

echo "Starting infrastructure services..."
docker compose -f docker-compose.infra.yml up -d

echo ""
echo "Waiting for PostgreSQL to be healthy..."
for i in {1..30}; do
    if docker exec second-brain-db pg_isready -U secondbrain >/dev/null 2>&1; then
        echo "PostgreSQL ready!"
        break
    fi
    sleep 1
done

echo ""
echo "=== Infrastructure Running ==="
echo ""
echo "Services:"
echo "  PostgreSQL: localhost:5432"
echo "  ChromaDB:   localhost:8002"
echo ""
echo "Commands:"
echo "  View logs:  docker compose -f docker-compose.infra.yml logs -f"
echo "  Stop:       docker compose -f docker-compose.infra.yml down"
echo ""
