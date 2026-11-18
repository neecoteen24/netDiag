cat << 'EOF' > scripts/capture_diag.sh
#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-example.com}"
PORTS="${2:-80,443}"
IFACE="${3:-any}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CAPTURE_DIR="$PROJECT_ROOT/captures"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
SAFE_TARGET="${TARGET//[^a-zA-Z0-9.-]/_}"
PCAP_FILE="$CAPTURE_DIR/capture_${SAFE_TARGET}_${TIMESTAMP}.pcap"

mkdir -p "$CAPTURE_DIR"

if ! command -v tcpdump >/dev/null 2>&1; then
    echo "[!] tcpdump is not installed. Run: sudo apt install -y tcpdump" >&2
    exit 1
fi

echo "[*] Starting packet capture on $IFACE -> $PCAP_FILE"
sudo tcpdump -i "$IFACE" -w "$PCAP_FILE" >/dev/null 2>&1 &
TCPDUMP_PID=$!
sleep 1

cd "$PROJECT_ROOT"
[[ -f "venv/bin/activate" ]] && source "venv/bin/activate"

python3 main.py --target "$TARGET" --ports "$PORTS" --no-trace

sleep 1
sudo kill -INT "$TCPDUMP_PID" 2>/dev/null || true
wait "$TCPDUMP_PID" 2>/dev/null || true

echo "[+] Capture saved: $PCAP_FILE"
EOF
chmod +x scripts/capture_diag.sh