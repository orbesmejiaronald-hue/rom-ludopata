#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

LOCAL_IP=$(hostname -I | awk '{print $1}')
TAILSCALE_IP=$(ip -4 addr show tailscale0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}')

echo "=========================================================="
echo "    ROM SPORT 2.0 - Servidor Cuantitativo de Apuestas     "
echo "=========================================================="
echo "IP Local (Wi-Fi):  http://${LOCAL_IP:-127.0.0.1}:5000"
if [ -n "$TAILSCALE_IP" ]; then
    echo "IP Tailscale VPN:  http://${TAILSCALE_IP}:5000"
fi
echo "=========================================================="
echo "Iniciando backend con Gunicorn en 0.0.0.0:5000..."

exec "$DIR/.venv/bin/python" -m gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120 app:app
