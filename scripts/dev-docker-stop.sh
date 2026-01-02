#!/bin/bash
# Stop Docker development mode
# Infrastructure (PostgreSQL, ChromaDB) keeps running

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Stopping Docker development containers..."
docker compose -f docker-compose.infra.yml -f docker-compose.dev.yml down --remove-orphans

echo ""
echo "Docker app containers stopped."
echo "Infrastructure (PostgreSQL, ChromaDB) still running."
echo ""
echo "To stop everything: ./scripts/infra-stop.sh"
