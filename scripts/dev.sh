#!/bin/bash
# dev.sh — Lance le backend et le frontend ensemble
#
# Usage: ./scripts/dev.sh
#
# Arrête proprement les deux serveurs avec Ctrl+C

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Scapin Development Server${NC}"
echo ""

# Vérifier si le backend tourne déjà
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend déjà en cours sur :8000${NC}"
    BACKEND_PID=""
else
    echo -e "${YELLOW}→ Démarrage du backend...${NC}"

    # Activer venv et lancer le backend en arrière-plan
    source .venv/bin/activate
    python -m src.jeeves.cli serve --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!

    # Attendre que le backend soit prêt
    echo -n "  Attente du backend"
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            echo ""
            echo -e "${GREEN}✓ Backend prêt sur http://localhost:8000${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done

    if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo ""
        echo -e "${RED}✗ Échec du démarrage du backend${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}→ Démarrage du frontend...${NC}"

# Fonction de nettoyage
cleanup() {
    echo ""
    echo -e "${YELLOW}→ Arrêt des serveurs...${NC}"

    # Arrêter le frontend (géré par npm qui reçoit le signal)

    # Arrêter le backend si on l'a démarré
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Backend arrêté${NC}"
    fi

    echo -e "${GREEN}✓ Terminé${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Lancer le frontend
cd web
npm run dev -- --host

# Si npm se termine, nettoyer
cleanup
