#!/bin/bash
set -e

# Load environment
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo ""
    echo "Please create .env from template:"
    echo "  cp .env.docker .env"
    echo ""
    echo "Then edit .env with your actual values:"
    echo "  - OBSIDIAN_VAULT_PATH (absolute path)"
    echo "  - ANTHROPIC_API_KEY (required)"
    echo "  - USER_ID (run: id -u)"
    echo "  - GROUP_ID (run: id -g)"
    exit 1
fi

echo "Starting Second Brain services..."
docker-compose up -d

echo ""
echo "✅ Services starting..."
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Postgres: localhost:5432"
echo "ChromaDB: http://localhost:8001"
echo ""
echo "Useful commands:"
echo "  Check status:  docker-compose ps"
echo "  View logs:     ./scripts/docker-logs.sh"
echo "  Stop all:      ./scripts/docker-stop.sh"
echo ""
echo "Wait ~30s for services to initialize, then visit:"
echo "  http://localhost:3000"
