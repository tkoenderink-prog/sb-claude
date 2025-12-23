#!/bin/bash
# View Docker logs for all services or specific service

if [ -z "$1" ]; then
    echo "Following logs for all services..."
    echo "Press Ctrl+C to exit"
    echo ""
    docker-compose logs -f
else
    echo "Following logs for service: $1"
    echo "Press Ctrl+C to exit"
    echo ""
    docker-compose logs -f "$1"
fi
