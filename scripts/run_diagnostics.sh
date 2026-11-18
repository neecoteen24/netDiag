#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-google.com}"
PORTS="${2:-80,443}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_DIR="$PROJECT_ROOT/reports"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
SAFE_TARGET="${TARGET//[^a-zA-Z0-9.-]/_}"
OUTPUT_FILE="$REPORT_DIR/netdiag_${SAFE_TARGET}_${TIMESTAMP}.json"

mkdir -p "$REPORT_DIR"

echo "[*] NetDiag Automated Runner"
echo "[*] Host: $(hostname) | Kernel: $(uname -r) | User: $(whoami)"
echo "[*] Target: $TARGET | Ports: $PORTS"

cd "$PROJECT_ROOT"

if [[ -f "venv/bin/activate" ]]; then
    source "venv/bin/activate"
fi

if python3 main.py --target "$TARGET" --ports "$PORTS" --no-trace > "$OUTPUT_FILE"; then
    echo "[+] Diagnostics completed successfully."
    echo "[+] Report saved to: $OUTPUT_FILE"
    exit 0
else
    EXIT_CODE=$?
    echo "[!] NetDiag encountered an execution error (exit code: $EXIT_CODE)." >&2
    exit "$EXIT_CODE"
fi
