#!/bin/bash

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Dossier du script
DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "🚀 Démarrage de AO Veille..."
echo ""

# --- Libérer le port 8000 si occupé ---
PORT_PID=$(lsof -ti :8000 2>/dev/null)
if [ -n "$PORT_PID" ]; then
    echo -e "${YELLOW}Port 8000 occupé — arrêt de l'ancien serveur...${NC}"
    kill $PORT_PID 2>/dev/null
    sleep 1
fi

# --- Lancer le backend ---
echo -e "${GREEN}[1/2] Démarrage du backend (port 8000)...${NC}"
cd "$DIR"
source venv/bin/activate
uvicorn api.main:app --port 8000 > /tmp/ao-veille-backend.log 2>&1 &
BACKEND_PID=$!

# Attendre que le backend soit prêt
sleep 2
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Erreur : le backend n'a pas démarré. Voir /tmp/ao-veille-backend.log${NC}"
    exit 1
fi
echo -e "${GREEN}   Backend OK (PID $BACKEND_PID)${NC}"

# --- Lancer le frontend ---
echo -e "${GREEN}[2/2] Démarrage du frontend (port 5173)...${NC}"
cd "$DIR/frontend"
npm run dev > /tmp/ao-veille-frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 2
echo -e "${GREEN}   Frontend OK (PID $FRONTEND_PID)${NC}"

echo ""
echo -e "${GREEN}✅ Tout est lancé !${NC}"
echo ""
echo "   Interface  →  http://localhost:5173"
echo "   API        →  http://localhost:8000"
echo ""
echo "   Appuie sur Ctrl+C pour tout arrêter."
echo ""

# --- Arrêter proprement avec Ctrl+C ---
trap "echo ''; echo 'Arrêt...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# Garder le script actif
wait
