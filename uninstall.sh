#!/usr/bin/env bash
set -euo pipefail

BASHRC="$HOME/.bashrc"
MARKER="# 3m"

if grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
    sed -i "/$MARKER/,/$MARKER/d" "$BASHRC"
    echo "  ✔ 3m aliases removed from $BASHRC"
else
    echo "  ⊘ 3m not installed in $BASHRC"
fi
