#!/usr/bin/env bash
# =============================================================================
# LOCAL AI VIDEO PRODUCTION STUDIO — LAUNCH SERVICE RUNNER
# =============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n${BLUE}======================================================${NC}"
echo -e "${BLUE}  STARTING LOCAL AI VIDEO PRODUCTION STUDIO          ${NC}"
echo -e "${BLUE}======================================================${NC}\n"

# 1. Start Docker services (PostgreSQL & Redis) if Docker is available
if command -v docker &>/dev/null && docker info &>/dev/null; then
    echo -e "${GREEN}==> Starting PostgreSQL and Redis containers...${NC}"
    docker compose up -d postgres redis
fi

# 2. Activate Python virtualenv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 3. Ensure logs directory exists
mkdir -p logs

# 4. Start FastAPI Backend
echo -e "${GREEN}==> Launching FastAPI backend server on http://localhost:8000...${NC}"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .backend.pid
echo -e "    Backend running (PID: $BACKEND_PID, logs in logs/backend.log)"

# 5. Start Next.js Frontend
if [ -d "frontend" ]; then
    echo -e "${GREEN}==> Launching Next.js frontend UI on http://localhost:3000...${NC}"
    cd frontend
    npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../.frontend.pid
    cd ..
    echo -e "    Frontend running (PID: $FRONTEND_PID, logs in logs/frontend.log)"
fi

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}  STUDIO READY!${NC}"
echo -e "  - Web Dashboard:     ${BLUE}http://localhost:3000${NC}"
echo -e "  - REST API Docs:     ${BLUE}http://localhost:8000/docs${NC}"
echo -e "  - Stop Studio:       ${YELLOW}./scripts/stop.sh${NC}"
echo -e "${GREEN}======================================================${NC}\n"
