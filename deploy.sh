#!/bin/bash
# ============================================================
# Affiliate Marketing Automation - Deployment Script
# ============================================================
set -e

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

echo "=========================================="
echo "  Affiliate Marketing Automation Deploy"
echo "=========================================="

# Check .env.prod exists
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "[!] File $ENV_FILE khong ton tai."
    echo "    Copy tu .env.example:"
    echo "    cp .env.example .env.prod"
    echo "    Sau do chinh sua cac gia tri trong .env.prod"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[!] Docker chua duoc cai dat. Vui long cai Docker Desktop."
    exit 1
fi

ACTION=${1:-up}

case $ACTION in
    up|start)
        echo ""
        echo "[1/3] Building Docker images..."
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE build

        echo ""
        echo "[2/3] Starting services..."
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d

        echo ""
        echo "[3/3] Waiting for services..."
        sleep 5

        echo ""
        echo "=========================================="
        echo "  Deployment hoan tat!"
        echo "=========================================="
        echo ""
        echo "  Frontend:  http://localhost:${FRONTEND_PORT:-3000}"
        echo "  Backend:   http://localhost:${BACKEND_PORT:-8000}"
        echo "  API Docs:  http://localhost:${BACKEND_PORT:-8000}/docs"
        echo "  Nginx:     http://localhost:${NGINX_PORT:-80}"
        echo ""
        echo "  Xem logs:  docker compose -f $COMPOSE_FILE logs -f"
        echo "  Dung:      ./deploy.sh stop"
        echo ""
        ;;

    stop|down)
        echo "Stopping services..."
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE down
        echo "Done."
        ;;

    restart)
        echo "Restarting services..."
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE down
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
        echo "Done."
        ;;

    logs)
        docker compose -f $COMPOSE_FILE logs -f ${2:-}
        ;;

    status)
        docker compose -f $COMPOSE_FILE ps
        ;;

    rebuild)
        echo "Rebuilding and restarting..."
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE build --no-cache
        docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
        echo "Done."
        ;;

    *)
        echo "Usage: ./deploy.sh [up|stop|restart|logs|status|rebuild]"
        echo ""
        echo "  up       - Build va khoi dong (mac dinh)"
        echo "  stop     - Dung tat ca services"
        echo "  restart  - Khoi dong lai"
        echo "  logs     - Xem logs (them ten service: ./deploy.sh logs backend)"
        echo "  status   - Xem trang thai services"
        echo "  rebuild  - Build lai tu dau (khong cache)"
        ;;
esac
