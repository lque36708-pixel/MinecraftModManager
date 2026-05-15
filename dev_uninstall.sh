#!/usr/bin/env bash
set -euo pipefail

BASHRC="$HOME/.bashrc"
MARKER="# 3m-dev"

if grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
    sed -i "/$MARKER/,/$MARKER/d" "$BASHRC"
    echo "  ✔ 3m-dev aliases removed from $BASHRC"
else
    echo "  ⊘ No 3m-dev aliases found in $BASHRC"
fi
