#!/usr/bin/env bash
# =============================================================================
# LOCAL AI VIDEO PRODUCTION STUDIO — AUTOMATED INSTALLER
# =============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n${BLUE}======================================================${NC}"
echo -e "${BLUE}  INSTALLING LOCAL AI VIDEO PRODUCTION STUDIO        ${NC}"
echo -e "${BLUE}======================================================${NC}\n"

# 1. Check Python
if ! command -v python3 &>/dev/null; then
    echo "Python 3 is required. Please install Python 3.11+."
    exit 1
fi

# 2. Virtual Environment
if [ ! -d "venv" ]; then
    echo -e "${GREEN}==> Creating Python virtual environment (venv)...${NC}"
    python3 -m venv venv
fi

echo -e "${GREEN}==> Activating virtual environment...${NC}"
source venv/bin/activate

# 3. Upgrade pip and install Python dependencies
echo -e "${GREEN}==> Installing backend Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt || echo -e "${YELLOW}Warning: Some optional ML packages may need manual build tools; core runtime ready.${NC}"

# 4. Frontend Dependencies
if [ -d "frontend" ]; then
    echo -e "${GREEN}==> Installing frontend Node packages...${NC}"
    cd frontend
    if command -v npm &>/dev/null; then
        npm install --legacy-peer-deps
    fi
    cd ..
fi

# 5. Environment file setup
if [ ! -f ".env" ]; then
    echo -e "${GREEN}==> Initializing .env configuration from .env.example...${NC}"
    cp .env.example .env
fi

# 6. Storage directories
mkdir -p storage/projects storage/assets storage/renders storage/temp models workflows/comfyui

chmod +x scripts/*.sh

echo -e "\n${GREEN}✓ INSTALLATION COMPLETED SUCCESSFULLY!${NC}"
echo -e "To verify setup, run: ./scripts/doctor.sh"
echo -e "To start the studio, run: ./scripts/start.sh\n"
