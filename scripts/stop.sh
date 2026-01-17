#!/bin/bash
# stop.sh — Arrête tous les processus Scapin
#
# Usage: ./scripts/stop.sh
#
# Tue tous les processus backend (uvicorn) et frontend (vite) de Scapin

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🛑 Arrêt des processus Scapin...${NC}"
echo ""

# Ports utilisés
BACKEND_PORT=8000
FRONTEND_PORT=5173

killed_something=false

# Arrêter les processus uvicorn Scapin
uvicorn_pids=$(pgrep -f "uvicorn.*src.jeeves" 2>/dev/null || true)
if [ -n "$uvicorn_pids" ]; then
    echo -e "${YELLOW}→ Arrêt des processus backend (uvicorn)${NC}"
    for pid in $uvicorn_pids; do
        cmd=$(ps -p $pid -o comm= 2>/dev/null || true)
        echo -e "  PID $pid ($cmd)"
        kill -15 $pid 2>/dev/null || true
    done
    killed_something=true
    sleep 1

    # Force kill si nécessaire
    uvicorn_pids=$(pgrep -f "uvicorn.*src.jeeves" 2>/dev/null || true)
    if [ -n "$uvicorn_pids" ]; then
        echo -e "${YELLOW}  Force kill...${NC}"
        echo "$uvicorn_pids" | xargs kill -9 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Backend arrêté${NC}"
fi

# Arrêter les processus vite Scapin
vite_pids=$(pgrep -f "vite.*scapin/web" 2>/dev/null || true)
if [ -n "$vite_pids" ]; then
    echo -e "${YELLOW}→ Arrêt des processus frontend (vite)${NC}"
    for pid in $vite_pids; do
        cmd=$(ps -p $pid -o comm= 2>/dev/null || true)
        echo -e "  PID $pid ($cmd)"
        kill -15 $pid 2>/dev/null || true
    done
    killed_something=true
    sleep 1

    # Force kill si nécessaire
    vite_pids=$(pgrep -f "vite.*scapin/web" 2>/dev/null || true)
    if [ -n "$vite_pids" ]; then
        echo -e "${YELLOW}  Force kill...${NC}"
        echo "$vite_pids" | xargs kill -9 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Frontend arrêté${NC}"
fi

# Vérifier les ports
echo ""
echo -e "${CYAN}Vérification des ports...${NC}"

backend_pids=$(lsof -ti :$BACKEND_PORT 2>/dev/null || true)
if [ -n "$backend_pids" ]; then
    echo -e "${YELLOW}→ Port $BACKEND_PORT encore occupé, force kill...${NC}"
    echo "$backend_pids" | xargs kill -9 2>/dev/null || true
    killed_something=true
    echo -e "${GREEN}✓ Port $BACKEND_PORT libéré${NC}"
else
    echo -e "  Port $BACKEND_PORT: ${GREEN}libre${NC}"
fi

frontend_pids=$(lsof -ti :$FRONTEND_PORT 2>/dev/null || true)
if [ -n "$frontend_pids" ]; then
    echo -e "${YELLOW}→ Port $FRONTEND_PORT encore occupé, force kill...${NC}"
    echo "$frontend_pids" | xargs kill -9 2>/dev/null || true
    killed_something=true
    echo -e "${GREEN}✓ Port $FRONTEND_PORT libéré${NC}"
else
    echo -e "  Port $FRONTEND_PORT: ${GREEN}libre${NC}"
fi

echo ""
if [ "$killed_something" = true ]; then
    echo -e "${GREEN}✓ Tous les processus Scapin ont été arrêtés${NC}"
else
    echo -e "${GREEN}✓ Aucun processus Scapin en cours${NC}"
fi
