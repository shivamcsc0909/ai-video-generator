#!/usr/bin/env bash
# =============================================================================
# LOCAL AI VIDEO PRODUCTION STUDIO — SYSTEM DIAGNOSTIC & DOCTOR SCRIPT
# =============================================================================
# Checks toolchains, dependencies, hardware, databases, and provider credentials.
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "\n${CYAN}======================================================${NC}"
echo -e "${CYAN}   LOCAL AI VIDEO PRODUCTION STUDIO — SYSTEM DOCTOR    ${NC}"
echo -e "${CYAN}======================================================${NC}\n"

ERRORS=0
WARNINGS=0

check_pass() {
    echo -e "  [${GREEN}✓ PASS${NC}] $1"
}

check_warn() {
    echo -e "  [${YELLOW}! WARN${NC}] $1"
    WARNINGS=$((WARNINGS + 1))
}

check_fail() {
    echo -e "  [${RED}✗ FAIL${NC}] $1"
    ERRORS=$((ERRORS + 1))
}

# 1. Operating System & Apple Silicon
echo -e "${BLUE}1. System & Architecture Check:${NC}"
OS_NAME=$(uname -s)
ARCH_NAME=$(uname -m)
if [ "$OS_NAME" = "Darwin" ]; then
    if [ "$ARCH_NAME" = "arm64" ]; then
        check_pass "macOS Apple Silicon ($ARCH_NAME) detected."
    else
        check_pass "macOS Intel ($ARCH_NAME) detected."
    fi
else
    check_pass "Operating System: $OS_NAME ($ARCH_NAME)"
fi

# RAM Check
if [ "$OS_NAME" = "Darwin" ]; then
    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    RAM_GB=$((RAM_BYTES / 1024 / 1024 / 1024))
    if [ "$RAM_GB" -ge 16 ]; then
        check_pass "Unified Memory / RAM: ${RAM_GB} GB (Good for local models & balanced inference)."
    elif [ "$RAM_GB" -ge 8 ]; then
        check_warn "Unified Memory: ${RAM_GB} GB. Recommend Balanced Mode with external AI provider fallback."
    else
        check_warn "Low Memory: ${RAM_GB} GB. Heavy local models may experience memory pressure."
    fi
fi

# 2. Runtimes: Python & Node
echo -e "\n${BLUE}2. Runtime Toolchains:${NC}"
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1)
    check_pass "Python: $PY_VER"
else
    check_fail "Python 3 is not installed or not in PATH."
fi

if command -v node &>/dev/null; then
    NODE_VER=$(node -v 2>&1)
    check_pass "Node.js: $NODE_VER"
else
    check_fail "Node.js is not installed."
fi

if command -v npm &>/dev/null; then
    NPM_VER=$(npm -v 2>&1)
    check_pass "npm: $NPM_VER"
else
    check_fail "npm is not installed."
fi

# 3. Media Processing: FFmpeg
echo -e "\n${BLUE}3. Media Processing Engine (FFmpeg):${NC}"
FFMPEG_BIN=""
if command -v ffmpeg &>/dev/null; then
    FFMPEG_BIN=$(command -v ffmpeg)
elif [ -f "/opt/homebrew/bin/ffmpeg" ]; then
    FFMPEG_BIN="/opt/homebrew/bin/ffmpeg"
elif [ -f "/usr/local/bin/ffmpeg" ]; then
    FFMPEG_BIN="/usr/local/bin/ffmpeg"
fi

if [ -n "$FFMPEG_BIN" ]; then
    FF_VER=$("$FFMPEG_BIN" -version 2>&1 | head -n 1)
    check_pass "FFmpeg installed at $FFMPEG_BIN ($FF_VER)"
else
    check_warn "FFmpeg not found in PATH. Run: brew install ffmpeg (Python fallback composition active)"
fi

# 4. Storage & File Permissions
echo -e "\n${BLUE}4. Storage Directories & Permissions:${NC}"
for DIR in storage/projects storage/assets storage/renders storage/temp models workflows/comfyui; do
    if [ -d "$DIR" ]; then
        if [ -w "$DIR" ]; then
            check_pass "Directory '$DIR' exists and is writable."
        else
            check_fail "Directory '$DIR' is not writable."
        fi
    else
        mkdir -p "$DIR" 2>/dev/null && check_pass "Created directory '$DIR'." || check_fail "Failed creating '$DIR'."
    fi
done

# 5. Infrastructure: PostgreSQL & Redis
echo -e "\n${BLUE}5. Infrastructure Services:${NC}"
if command -v docker &>/dev/null; then
    DOCKER_VER=$(docker --version)
    check_pass "Docker: $DOCKER_VER"
    if docker info &>/dev/null; then
        check_pass "Docker daemon is running."
    else
        check_warn "Docker daemon is not running. Start Docker Desktop to run PostgreSQL/Redis containers."
    fi
else
    check_warn "Docker not installed. Using local native PostgreSQL & Redis services if installed."
fi

# Check PostgreSQL port
if nc -z localhost 5432 2>/dev/null; then
    check_pass "PostgreSQL is reachable on port 5432."
else
    check_warn "PostgreSQL not reachable on port 5432. (Start via: docker compose up -d postgres)"
fi

# Check Redis port
if nc -z localhost 6379 2>/dev/null; then
    check_pass "Redis is reachable on port 6379."
else
    check_warn "Redis not reachable on port 6379. (Start via: docker compose up -d redis)"
fi

# 6. Local ComfyUI Inference
echo -e "\n${BLUE}6. Local AI Inference (ComfyUI):${NC}"
COMFY_URL="http://127.0.0.1:8188"
if curl -s --max-time 1.5 "$COMFY_URL/system_stats" &>/dev/null; then
    check_pass "Local ComfyUI is active and reachable at $COMFY_URL"
else
    check_warn "Local ComfyUI is not currently running at $COMFY_URL. System will gracefully use cloud providers (Gemini, Groq, Fal, Replicate) and local synthetic video generation."
fi

# 7. Ports Availability for Web Services
echo -e "\n${BLUE}7. Application Network Ports:${NC}"
for PORT in 8000 3000; do
    if nc -z localhost $PORT 2>/dev/null; then
        check_warn "Port $PORT is currently in use."
    else
        check_pass "Port $PORT is free and available."
    fi
done

# 8. Credential Encryption Setup
echo -e "\n${BLUE}8. Security & Encryption Key:${NC}"
if [ -n "$ENCRYPTION_KEY" ]; then
    check_pass "ENCRYPTION_KEY is set in environment."
elif [ -f "$HOME/.videostudio_key" ]; then
    check_pass "Local encryption key persisted at $HOME/.videostudio_key"
else
    check_pass "Encryption service will auto-generate and persist key to ~/.videostudio_key upon first run."
fi

# Diagnostic Summary
echo -e "\n${CYAN}======================================================${NC}"
if [ "$ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CRITICAL CHECKS PASSED.${NC} System is ready to run!"
    if [ "$WARNINGS" -gt 0 ]; then
        echo -e "${YELLOW}  ($WARNINGS non-critical warnings noted above).${NC}"
    fi
else
    echo -e "${RED}✗ $ERRORS CRITICAL ERRORS FOUND.${NC} Please review the issues above before starting."
fi
echo -e "${CYAN}======================================================${NC}\n"

exit $ERRORS
