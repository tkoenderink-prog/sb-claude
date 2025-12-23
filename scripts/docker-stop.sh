#!/bin/bash
echo "Stopping Second Brain services..."
docker-compose down

echo ""
echo "✅ All services stopped"
echo ""
echo "To start again: ./scripts/docker-start.sh"
echo "To remove volumes (⚠️  deletes data): docker-compose down -v"
