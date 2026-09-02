#!/usr/bin/env bash
set -e

echo "==================================================="
echo "  AetherPhoenix AI Desktop Suite - Docker Launcher"
echo "==================================================="
echo ""

if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed or not in PATH."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "[ERROR] Docker daemon is not running."
    exit 1
fi

echo "[1/3] Docker daemon is active and running."
echo ""

echo "Select action:"
echo "[1] Start Docker Containers (docker compose up --build -d)"
echo "[2] Stop Docker Containers (docker compose down)"
echo "[3] View Container Logs (docker compose logs -f)"
echo "[4] Check Container Status (docker compose ps)"
read -p "Enter choice [1-4] (default 1): " CHOICE
CHOICE=${CHOICE:-1}

case $CHOICE in
    1)
        echo ""
        echo "[2/3] Building and starting containers..."
        docker compose up --build -d
        echo ""
        echo "[3/3] Containers started successfully!"
        docker compose ps
        echo ""
        echo "==================================================="
        echo "  AetherPhoenix Docker Suite is running!"
        echo "  - Frontend: http://localhost:5173"
        echo "  - Backend API: http://localhost:8000"
        echo "  - Swagger Docs: http://localhost:8000/docs"
        echo "==================================================="
        ;;
    2)
        docker compose down
        ;;
    3)
        docker compose logs -f
        ;;
    4)
        docker compose ps
        ;;
    *)
        echo "Invalid choice."
        ;;
esac
