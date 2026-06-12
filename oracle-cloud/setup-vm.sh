#!/bin/bash
# Fly Intelligence Platform — Oracle Cloud VM setup (Ubuntu ARM)
# Run on a fresh Oracle Cloud Ampere A1 instance as ubuntu user:
#   curl -fsSL https://raw.githubusercontent.com/Hammertymm/scorefly/main/oracle-cloud/setup-vm.sh | bash
# Or after git clone:
#   bash oracle-cloud/setup-vm.sh

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Hammertymm/scorefly.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/scorefly}"
DATA_DIR="/data/flytime"

echo "=== Fly Intelligence Platform — Oracle Cloud Setup ==="

# 1. System packages
sudo apt-get update -qq
sudo apt-get install -y -qq git curl ca-certificates

# 2. Docker (official install script)
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  echo "Docker installed. You may need to log out/in for group membership."
fi

# 3. Data volume directory (persistent across container rebuilds)
sudo mkdir -p "$DATA_DIR/exports"
sudo chown -R "$USER:$USER" "$DATA_DIR"

# 4. Clone or update repo
if [ -d "$INSTALL_DIR/.git" ]; then
  cd "$INSTALL_DIR"
  git pull --ff-only
else
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# Use Oracle Cloud compose file with bind-mounted /data/flytime
COMPOSE_FILE="-f docker-compose.oracle.yml"
docker compose $COMPOSE_FILE down 2>/dev/null || true
docker compose $COMPOSE_FILE up -d --build

# 6. Init database (safe to re-run)
docker compose $COMPOSE_FILE exec -T fly-intelligence python main.py init

# 7. Open port 8787 in local firewall if ufw is active
if command -v ufw &>/dev/null && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow 8787/tcp comment "Fly Intelligence dashboard"
fi

# 8. Get public IP
PUBLIC_IP=$(curl -s -H "Metadata-Flavor: Oracle" http://169.254.169.254/opc/v1/v1/instance/metadata/publicIp 2>/dev/null || true)
if [ -z "$PUBLIC_IP" ]; then
  PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_VM_PUBLIC_IP")
fi

echo ""
echo "=== DONE ==="
echo ""
echo "Dashboard:  http://${PUBLIC_IP}:8787/"
echo "Health:     http://${PUBLIC_IP}:8787/api/health"
echo ""
echo "IMPORTANT — Oracle Cloud Console:"
echo "  1. Networking > Virtual cloud networks > your VCN > Security List"
echo "  2. Add Ingress Rule: TCP port 8787, source 0.0.0.0/0 (or your home IP only)"
echo ""
echo "Upload your local database (run from your Windows laptop):"
echo "  cd scorefly/oracle-cloud"
echo "  .\\upload-db.ps1 -VmIp ${PUBLIC_IP} -KeyPath C:\\path\\to\\your-key.key"
echo ""
echo "Or manually:"
echo "  scp flytime-engine/data/flytime_engine.db ubuntu@${PUBLIC_IP}:/data/flytime/"
echo "  ssh ubuntu@${PUBLIC_IP} 'cd ~/scorefly && docker compose -f docker-compose.oracle.yml restart'"
echo ""
