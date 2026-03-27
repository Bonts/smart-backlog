#!/usr/bin/env bash
# Smart Backlog — Oracle Cloud VM Setup Script
# Run as root: sudo ./setup.sh
set -euo pipefail

APP_DIR="/opt/smart-backlog"
APP_USER="smart-backlog"
REPO_URL="https://github.com/Bonts/smart-backlog.git"

# Detect system Python version (Ubuntu 24.04 = 3.12, Ubuntu 22.04 = 3.10)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Detected Python ${PYTHON_VERSION}"

echo "=== Smart Backlog — Server Setup ==="

# 1. System packages
echo "[1/7] Installing system packages..."
apt-get update
apt-get install -y --no-install-recommends \
    software-properties-common \
    python3 \
    python3-venv \
    python3-dev \
    python3-pip \
    ffmpeg \
    git

# 2. Create 1 GB swap (E2.1.Micro has only 1 GB RAM)
echo "[2/7] Setting up swap..."
if [ ! -f /swapfile ]; then
    fallocate -l 1G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "  Swap enabled (1 GB)"
else
    echo "  Swap already exists"
fi

# 3. Create service user
echo "[3/7] Creating service user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" "$APP_USER"
fi

# 4. Clone repository
echo "[4/7] Cloning repository..."
if [ -d "$APP_DIR" ]; then
    echo "  Directory $APP_DIR already exists, pulling latest..."
    cd "$APP_DIR"
    sudo -u "$APP_USER" git pull || true
else
    git clone "$REPO_URL" "$APP_DIR"
    chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
fi

# 5. Python virtual environment
echo "[5/7] Setting up Python virtual environment..."
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv .venv
sudo -u "$APP_USER" .venv/bin/pip install --upgrade pip
sudo -u "$APP_USER" .venv/bin/pip install -r requirements.txt

# 6. Create data directory and .env
echo "[6/7] Setting up data directory and .env..."
sudo -u "$APP_USER" mkdir -p "$APP_DIR/data"

if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chown "$APP_USER":"$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo "  Created .env from template — edit it with your API keys!"
fi

# 7. Install systemd service
echo "[7/7] Installing systemd service..."
cp "$APP_DIR/deploy/smart-backlog.service" /etc/systemd/system/smart-backlog.service
systemctl daemon-reload
systemctl enable smart-backlog

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit /opt/smart-backlog/.env with your API keys"
echo "  2. Start the bot: sudo systemctl start smart-backlog"
echo "  3. Check status:  sudo systemctl status smart-backlog"
echo "  4. View logs:     sudo journalctl -u smart-backlog -f"
