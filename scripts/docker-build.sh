#!/bin/bash
set -e

echo "Building Docker images for Second Brain..."
docker-compose build --parallel

echo ""
echo "✅ Build complete!"
echo ""
echo "Next steps:"
echo "  1. Copy .env.docker to .env and configure:"
echo "     cp .env.docker .env"
echo "  2. Edit .env with your actual values"
echo "  3. Start services:"
echo "     ./scripts/docker-start.sh"
