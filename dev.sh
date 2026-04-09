#!/bin/bash
# Inicia todos os servicos do Oratoria Avaliador em 1 comando
#
# Uso:
#   ./dev.sh           # roda local
#   ./dev.sh --share   # roda local + cria tunnel publico (cloudflared)

set -e

cd "$(dirname "$0")"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_DIR=".dev-logs"
mkdir -p "$LOG_DIR"

API_LOG="$LOG_DIR/api.log"
ML_LOG="$LOG_DIR/ml-worker.log"
WEB_LOG="$LOG_DIR/web.log"
TUNNEL_API_LOG="$LOG_DIR/tunnel-api.log"
TUNNEL_WEB_LOG="$LOG_DIR/tunnel-web.log"

PIDS=()

# Verificar portas livres
check_port_free() {
    local port=$1
    local name=$2
    if ss -tln 2>/dev/null | grep -q ":$port "; then
        local pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | head -1)
        local cmd=""
        [ -n "$pid" ] && cmd=$(ps -p "$pid" -o cmd= 2>/dev/null | head -c 80)
        echo -e "${RED}ERRO: Porta $port ($name) ja esta em uso${NC}"
        [ -n "$pid" ] && echo -e "${RED}  PID $pid: $cmd${NC}"
        echo -e "${YELLOW}  Mate o processo antes de rodar dev.sh: kill $pid${NC}"
        return 1
    fi
    return 0
}

PORTS_OK=true
check_port_free 7860 "ML Worker" || PORTS_OK=false
check_port_free 8002 "API"       || PORTS_OK=false
check_port_free 3000 "Frontend"  || PORTS_OK=false

if [ "$PORTS_OK" = false ]; then
    echo -e "\n${RED}Aborte: portas em conflito.${NC}"
    exit 1
fi

# Verificar modelos do MediaPipe (baixar se necessario)
MEDIAPIPE_DIR="/tmp/mediapipe_models"
mkdir -p "$MEDIAPIPE_DIR"

download_model() {
    local file=$1
    local url=$2
    if [ ! -f "$MEDIAPIPE_DIR/$file" ]; then
        echo -e "${YELLOW}Baixando MediaPipe model: $file...${NC}"
        curl -sL -o "$MEDIAPIPE_DIR/$file" "$url" && \
            echo -e "${GREEN}  ✓ $file${NC}" || \
            echo -e "${RED}  ✗ Falha ao baixar $file${NC}"
    fi
}

download_model "pose_landmarker.task" "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
download_model "hand_landmarker.task" "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
download_model "face_landmarker.task" "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"

cleanup() {
    echo -e "\n${YELLOW}Encerrando servicos...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    pkill -f "uvicorn app.main" 2>/dev/null || true
    pkill -f "ml-worker/app.py" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    echo -e "${GREEN}OK.${NC}"
    exit 0
}
trap cleanup INT TERM

# ============================================================
# 1. ML WORKER
# ============================================================
echo -e "${BLUE}[1/3] Iniciando ML Worker (porta 7860)...${NC}"
(
    cd ml-worker
    source .venv/bin/activate
    uvicorn app:app --host 0.0.0.0 --port 7860
) > "$ML_LOG" 2>&1 &
PIDS+=($!)

# ============================================================
# 2. API
# ============================================================
echo -e "${BLUE}[2/3] Iniciando API (porta 8002)...${NC}"
(
    cd apps/api
    source .venv/bin/activate
    uvicorn app.main:app --reload --port 8002 --host 0.0.0.0
) > "$API_LOG" 2>&1 &
PIDS+=($!)

# ============================================================
# 3. FRONTEND
# ============================================================
echo -e "${BLUE}[3/3] Iniciando Frontend (porta 3000)...${NC}"
(
    cd apps/web
    npm run dev
) > "$WEB_LOG" 2>&1 &
PIDS+=($!)

# Aguardar tudo subir
echo -e "\n${YELLOW}Aguardando servicos ficarem prontos...${NC}"
sleep 8

# Verificar saude
check_service() {
    local name=$1
    local url=$2
    if curl -s --max-time 3 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ $name${NC}"
        return 0
    else
        echo -e "${RED}  ✗ $name (veja $LOG_DIR/)${NC}"
        return 1
    fi
}

echo -e "\n${BLUE}Verificando servicos:${NC}"
check_service "ML Worker  http://localhost:7860/health" "http://localhost:7860/health" || true
check_service "API        http://localhost:8002/health" "http://localhost:8002/health" || true
check_service "Frontend   http://localhost:3000"        "http://localhost:3000" || true

# ============================================================
# MODO --share: criar tunneis
# ============================================================
if [ "$1" = "--share" ]; then
    echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Modo SHARE: criando tunneis publicos...${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    if ! command -v cloudflared &> /dev/null; then
        echo -e "${RED}cloudflared nao encontrado. Instale com: sudo apt install cloudflared${NC}"
        cleanup
        exit 1
    fi

    # Tunnel API
    echo -e "\n${BLUE}Criando tunnel da API...${NC}"
    cloudflared tunnel --url http://localhost:8002 > "$TUNNEL_API_LOG" 2>&1 &
    PIDS+=($!)

    API_TUNNEL_URL=""
    for i in {1..30}; do
        sleep 1
        API_TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_API_LOG" 2>/dev/null | head -1 || true)
        [ -n "$API_TUNNEL_URL" ] && break
    done

    if [ -z "$API_TUNNEL_URL" ]; then
        echo -e "${RED}Falha ao criar tunnel da API${NC}"
        cleanup
        exit 1
    fi
    echo -e "${GREEN}  API: $API_TUNNEL_URL${NC}"

    # Atualizar .env.local e reiniciar Next.js
    echo -e "\n${BLUE}Atualizando NEXT_PUBLIC_API_URL e reiniciando frontend...${NC}"
    echo "NEXT_PUBLIC_API_URL=$API_TUNNEL_URL" > apps/web/.env.local

    # Matar e religar o Next dev para pegar o novo env
    pkill -f "next dev" 2>/dev/null || true
    sleep 2
    (
        cd apps/web
        npm run dev
    ) > "$WEB_LOG" 2>&1 &
    PIDS+=($!)

    sleep 6

    # Tunnel Frontend
    echo -e "${BLUE}Criando tunnel do Frontend...${NC}"
    cloudflared tunnel --url http://localhost:3000 > "$TUNNEL_WEB_LOG" 2>&1 &
    PIDS+=($!)

    WEB_TUNNEL_URL=""
    for i in {1..30}; do
        sleep 1
        WEB_TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_WEB_LOG" 2>/dev/null | head -1 || true)
        [ -n "$WEB_TUNNEL_URL" ] && break
    done

    if [ -z "$WEB_TUNNEL_URL" ]; then
        echo -e "${RED}Falha ao criar tunnel do Frontend${NC}"
        cleanup
        exit 1
    fi
    echo -e "${GREEN}  Frontend: $WEB_TUNNEL_URL${NC}"

    echo -e "\n${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}LINK PARA O MENTOR:${NC}"
    echo -e "${GREEN}  $WEB_TUNNEL_URL${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
fi

echo -e "\n${CYAN}Servicos rodando.${NC}"
echo -e "${CYAN}Logs em: $LOG_DIR/${NC}"
echo -e "${YELLOW}Pressione Ctrl+C para encerrar tudo${NC}\n"

# Tail dos logs em paralelo (so o resumo)
tail -f "$API_LOG" "$ML_LOG" "$WEB_LOG" 2>/dev/null &
PIDS+=($!)

wait
