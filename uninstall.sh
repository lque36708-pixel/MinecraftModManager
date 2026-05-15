#!/usr/bin/env bash
set -euo pipefail

BASHRC="$HOME/.bashrc"
MARKER="# mmm"

if grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
    sed -i "/$MARKER/,/$MARKER/d" "$BASHRC"
    echo "  ✔ mmm aliases removed from $BASHRC"
else
    echo "  ⊘ mmm not installed in $BASHRC"
fi
