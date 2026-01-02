#!/bin/bash
# Stop all Docker services including infrastructure

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Stopping all Docker services..."

# Stop dev containers if running
docker compose -f docker-compose.infra.yml -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true

# Stop production containers if running
docker compose down --remove-orphans 2>/dev/null || true

# Stop infrastructure
docker compose -f docker-compose.infra.yml down --remove-orphans

echo ""
echo "All Docker services stopped."
echo ""
echo "Data volumes preserved. To remove:"
echo "  docker volume rm second-brain-app_postgres_data second-brain-app_chroma_data"
