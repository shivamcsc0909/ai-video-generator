#!/usr/bin/env bash
# =============================================================================
# LOCAL AI VIDEO PRODUCTION STUDIO — SHUTDOWN SCRIPT
# =============================================================================

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${YELLOW}Stopping AI Video Studio services...${NC}"

# Stop Backend
if [ -f ".backend.pid" ]; then
    PID=$(cat .backend.pid)
    kill "$PID" 2>/dev/null && echo -e "  Stopped FastAPI backend (PID: $PID)"
    rm -f .backend.pid
fi

# Stop Frontend
if [ -f ".frontend.pid" ]; then
    PID=$(cat .frontend.pid)
    kill "$PID" 2>/dev/null && echo -e "  Stopped Next.js frontend (PID: $PID)"
    rm -f .frontend.pid
fi

# Kill any orphaned processes on port 8000 and 3000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

echo -e "${GREEN}All services stopped.${NC}"
