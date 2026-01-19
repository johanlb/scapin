#!/bin/bash
# dev.sh — Lance le backend et le frontend ensemble
#
# Usage: ./scripts/dev.sh
#
# Fonctionnalités:
# - Tue les processus zombies des sessions précédentes
# - Vérifie et libère les ports 8000 (backend) et 5173 (frontend)
# - Arrête proprement les deux serveurs avec Ctrl+C

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Ports utilisés
BACKEND_PORT=8000
FRONTEND_PORT=5173

# PIDs des processus démarrés
BACKEND_PID=""
FRONTEND_PID=""

echo -e "${BLUE}🚀 Scapin Development Server${NC}"
echo ""

# =============================================================================
# Fonctions utilitaires
# =============================================================================

# Trouver les PIDs utilisant un port
get_pids_on_port() {
    local port=$1
    lsof -ti :$port 2>/dev/null || true
}

# Tuer les processus sur un port
kill_port() {
    local port=$1
    local pids=$(get_pids_on_port $port)

    if [ -n "$pids" ]; then
        echo -e "${YELLOW}→ Port $port occupé, arrêt des processus...${NC}"
        for pid in $pids; do
            # Vérifier si c'est un de nos processus (uvicorn, node, vite)
            local cmd=$(ps -p $pid -o comm= 2>/dev/null || true)
            if [ -n "$cmd" ]; then
                echo -e "  Arrêt de $cmd (PID: $pid)"
                kill -15 $pid 2>/dev/null || true
            fi
        done

        # Attendre un peu puis forcer si nécessaire
        sleep 1
        pids=$(get_pids_on_port $port)
        if [ -n "$pids" ]; then
            echo -e "${YELLOW}  Force kill des processus restants...${NC}"
            for pid in $pids; do
                kill -9 $pid 2>/dev/null || true
            done
            sleep 0.5
        fi

        # Vérifier que le port est libre
        pids=$(get_pids_on_port $port)
        if [ -n "$pids" ]; then
            echo -e "${RED}✗ Impossible de libérer le port $port${NC}"
            echo -e "  PIDs restants: $pids"
            echo -e "  Essayez: sudo lsof -ti :$port | xargs kill -9"
            return 1
        fi
        echo -e "${GREEN}✓ Port $port libéré${NC}"
    fi
    return 0
}

# Tuer les processus zombies Scapin
kill_scapin_zombies() {
    echo -e "${CYAN}🧹 Nettoyage des processus précédents...${NC}"

    # Tuer les processus uvicorn/python liés à scapin
    local uvicorn_pids=$(pgrep -f "uvicorn.*src.frontin" 2>/dev/null || true)
    if [ -n "$uvicorn_pids" ]; then
        echo -e "  Arrêt des processus uvicorn Scapin"
        echo "$uvicorn_pids" | xargs kill -15 2>/dev/null || true
        sleep 1
        # Force kill si encore présents
        uvicorn_pids=$(pgrep -f "uvicorn.*src.frontin" 2>/dev/null || true)
        if [ -n "$uvicorn_pids" ]; then
            echo "$uvicorn_pids" | xargs kill -9 2>/dev/null || true
        fi
    fi

    # Tuer les processus vite liés au projet web scapin
    local vite_pids=$(pgrep -f "vite.*scapin/web" 2>/dev/null || true)
    if [ -n "$vite_pids" ]; then
        echo -e "  Arrêt des processus Vite Scapin"
        echo "$vite_pids" | xargs kill -15 2>/dev/null || true
        sleep 1
        vite_pids=$(pgrep -f "vite.*scapin/web" 2>/dev/null || true)
        if [ -n "$vite_pids" ]; then
            echo "$vite_pids" | xargs kill -9 2>/dev/null || true
        fi
    fi

    # Libérer les ports
    kill_port $BACKEND_PORT || exit 1
    kill_port $FRONTEND_PORT || exit 1

    echo -e "${GREEN}✓ Nettoyage terminé${NC}"
    echo ""
}

# Fonction de nettoyage à la sortie
cleanup() {
    echo ""
    echo -e "${YELLOW}→ Arrêt des serveurs...${NC}"

    # Arrêter le frontend
    if [ -n "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        kill -15 $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Frontend arrêté${NC}"
    fi

    # Arrêter le backend
    if [ -n "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        kill -15 $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Backend arrêté${NC}"
    fi

    # Nettoyage final des ports (au cas où)
    sleep 0.5
    local backend_pids=$(get_pids_on_port $BACKEND_PORT)
    if [ -n "$backend_pids" ]; then
        echo "$backend_pids" | xargs kill -9 2>/dev/null || true
    fi
    local frontend_pids=$(get_pids_on_port $FRONTEND_PORT)
    if [ -n "$frontend_pids" ]; then
        echo "$frontend_pids" | xargs kill -9 2>/dev/null || true
    fi

    echo -e "${GREEN}✓ Terminé${NC}"
    exit 0
}

# Capturer les signaux
trap cleanup SIGINT SIGTERM EXIT

# =============================================================================
# Démarrage
# =============================================================================

# 1. Nettoyer les processus zombies
kill_scapin_zombies

# 2. Démarrer le backend
echo -e "${YELLOW}→ Démarrage du backend sur :$BACKEND_PORT...${NC}"

# Activer venv et lancer le backend en arrière-plan
source .venv/bin/activate
python -m src.frontin.cli serve --host 0.0.0.0 --port $BACKEND_PORT 2>&1 &
BACKEND_PID=$!

# Attendre que le backend soit prêt (max 30 secondes)
echo -n "  Attente du backend"
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓ Backend prêt sur http://localhost:$BACKEND_PORT${NC}"
        break
    fi

    # Vérifier si le processus est encore en vie
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo ""
        echo -e "${RED}✗ Le backend s'est arrêté de manière inattendue${NC}"
        echo -e "  Vérifiez les logs ci-dessus pour les erreurs"
        exit 1
    fi

    echo -n "."
    sleep 1
done

# Vérification finale
if ! curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null 2>&1; then
    echo ""
    echo -e "${RED}✗ Timeout: le backend n'a pas démarré en 30 secondes${NC}"
    exit 1
fi

echo ""

# 3. Démarrer le frontend
echo -e "${YELLOW}→ Démarrage du frontend sur :$FRONTEND_PORT...${NC}"

cd web
npm run dev -- --host --port $FRONTEND_PORT &
FRONTEND_PID=$!

# Attendre que le frontend soit prêt (max 30 secondes)
echo -n "  Attente du frontend"
for i in {1..30}; do
    if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓ Frontend prêt sur http://localhost:$FRONTEND_PORT${NC}"
        break
    fi

    # Vérifier si le processus est encore en vie
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo ""
        echo -e "${RED}✗ Le frontend s'est arrêté de manière inattendue${NC}"
        exit 1
    fi

    echo -n "."
    sleep 1
done

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Scapin est prêt !${NC}"
echo -e "  Backend:  ${CYAN}http://localhost:$BACKEND_PORT${NC}"
echo -e "  Frontend: ${CYAN}http://localhost:$FRONTEND_PORT${NC}"
echo -e "  API Docs: ${CYAN}http://localhost:$BACKEND_PORT/docs${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Appuyez sur Ctrl+C pour arrêter les serveurs${NC}"
echo ""

# Attendre que les processus se terminent
wait $FRONTEND_PID $BACKEND_PID 2>/dev/null || true
