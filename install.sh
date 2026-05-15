#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
BASHRC="$HOME/.bashrc"
MARKER="# mmm"

echo "  › Installing mmm — adding alias to $BASHRC"

if grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
    echo "  ✔ Already installed. Updating path..."
    sed -i "/$MARKER/,/$MARKER/d" "$BASHRC"
fi

cat >> "$BASHRC" <<EOF

$MARKER
alias mmm="python3 $SCRIPT_DIR/mmm.py"
$MARKER
EOF

echo "  ✔ Done. Restart your shell or run: source $BASHRC"
