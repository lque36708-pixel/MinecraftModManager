#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
BASHRC="$HOME/.bashrc"
MARKER="# 3m-dev"

echo "  › 3m dev install — adding aliases to $BASHRC"

if grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
    echo "  ✔ Aliases already installed. Updating path..."
    sed -i "/$MARKER/,/$MARKER/d" "$BASHRC"
fi

cat >> "$BASHRC" <<EOF

$MARKER
alias 3m="python3 $SCRIPT_DIR/3m.py"
alias mmm="python3 $SCRIPT_DIR/3m.py"
$MARKER
EOF

echo "  ✔ Done. Sourcing $BASHRC ..."
# shellcheck disable=SC1090
source "$BASHRC" 2>/dev/null || true
echo "  ✔ Aliases active in this shell. Run: 3m --version"
