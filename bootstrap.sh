#!/usr/bin/env bash
# bootstrap.sh — curl | bash entry point for the installer tool
#
# Usage on a fresh server:
#   curl -fsSL https://raw.githubusercontent.com/ksnsk-nakul/installer/main/bootstrap.sh | bash
#
# What it does:
#   1. Detects the OS (Ubuntu/Debian or fallback)
#   2. Installs Python 3.11+ if missing
#   3. Installs pip and the installer-tool package
#   4. Starts the web dashboard on port 8080
#   5. Prints the access URL

set -euo pipefail

INSTALLER_PKG="${INSTALLER_PKG:-installer-tool}"
INSTALLER_REPO="${INSTALLER_REPO:-https://github.com/ksnsk-nakul/installer.git}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8080}"
LOG_FILE="/tmp/installer-bootstrap.log"

# ── helpers ──────────────────────────────────────────────────────────────────

log()  { echo "[installer] $*" | tee -a "$LOG_FILE"; }
die()  { echo "[installer] ERROR: $*" | tee -a "$LOG_FILE" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1; }

# ── detect OS ────────────────────────────────────────────────────────────────

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "${ID:-unknown}"
    elif uname -s 2>/dev/null | grep -qi darwin; then
        echo "macos"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
log "Detected OS: $OS"

# ── install Python 3.11+ ─────────────────────────────────────────────────────

install_python() {
    if need python3; then
        PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
            log "Python $PY_VER already installed — skipping"
            return
        fi
    fi

    log "Installing Python 3.11..."
    case "$OS" in
        ubuntu|debian)
            apt-get update -y >> "$LOG_FILE" 2>&1
            apt-get install -y python3.11 python3.11-venv python3-pip >> "$LOG_FILE" 2>&1
            update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 >> "$LOG_FILE" 2>&1 || true
            ;;
        fedora|centos|rhel|rocky|almalinux)
            dnf install -y python3.11 python3-pip >> "$LOG_FILE" 2>&1
            ;;
        alpine)
            apk add --no-cache python3 py3-pip >> "$LOG_FILE" 2>&1
            ;;
        *)
            die "Unsupported OS: $OS. Please install Python 3.11+ manually."
            ;;
    esac
}

install_python

# ── ensure pip ───────────────────────────────────────────────────────────────

if ! need pip3 && ! need pip; then
    log "Installing pip..."
    python3 -m ensurepip --upgrade >> "$LOG_FILE" 2>&1 || \
        curl -fsSL https://bootstrap.pypa.io/get-pip.py | python3 >> "$LOG_FILE" 2>&1
fi

PIP=$(need pip3 && echo pip3 || echo pip)

# ── install installer-tool ───────────────────────────────────────────────────

log "Installing installer-tool..."
if [ -d /opt/installer ]; then
    log "Found existing /opt/installer — pulling latest..."
    git -C /opt/installer pull --rebase >> "$LOG_FILE" 2>&1
else
    if need git; then
        git clone "$INSTALLER_REPO" /opt/installer >> "$LOG_FILE" 2>&1
    else
        log "git not found — installing via pip from PyPI..."
        $PIP install --upgrade "$INSTALLER_PKG" >> "$LOG_FILE" 2>&1
    fi
fi

if [ -d /opt/installer ]; then
    $PIP install -e /opt/installer >> "$LOG_FILE" 2>&1
fi

# Verify install
if ! need installer; then
    # Ensure user-local bin is on PATH
    export PATH="$HOME/.local/bin:$PATH"
fi

need installer || die "installer command not found after install. Check $LOG_FILE"
log "installer-tool installed: $(installer --help 2>&1 | head -1)"

# ── detect server IP ─────────────────────────────────────────────────────────

SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$SERVER_IP" ] && SERVER_IP=$(curl -fsSL --max-time 5 https://ipecho.net/plain 2>/dev/null || echo "localhost")

# ── start dashboard ──────────────────────────────────────────────────────────

log "Starting web dashboard on port $DASHBOARD_PORT..."
nohup installer dashboard --port "$DASHBOARD_PORT" >> "$LOG_FILE" 2>&1 &
DASHBOARD_PID=$!
sleep 2

if kill -0 "$DASHBOARD_PID" 2>/dev/null; then
    log "Dashboard started (PID $DASHBOARD_PID)"
else
    log "Dashboard process exited — see $LOG_FILE for details"
fi

# ── done ─────────────────────────────────────────────────────────────────────

cat <<BANNER

╔═══════════════════════════════════════════════════════╗
║           installer-tool bootstrap complete           ║
╠═══════════════════════════════════════════════════════╣
║  Open the web dashboard in your browser:              ║
║  http://${SERVER_IP}:${DASHBOARD_PORT}
║                                                       ║
║  Or use the CLI directly:                             ║
║    installer detect                                   ║
║    installer install --config installer.yaml          ║
║    installer verify  --config installer.yaml          ║
║                                                       ║
║  Bootstrap log: $LOG_FILE
╚═══════════════════════════════════════════════════════╝

BANNER
