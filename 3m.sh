#!/usr/bin/env bash
# 3m.sh — wrapper cho 3m.py
# Cài vào PATH: sudo ln -s /path/to/3m.sh /usr/local/bin/3m
# Hoặc: chmod +x 3m.sh && ./3m.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/3m.py"

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "✗ Không tìm thấy 3m.py bên cạnh 3m.sh" >&2
    exit 1
fi

# Ưu tiên python3, fallback về python
if command -v python3 &>/dev/null; then
    exec python3 "$PYTHON_SCRIPT" "$@"
elif command -v python &>/dev/null; then
    exec python "$PYTHON_SCRIPT" "$@"
else
    echo "✗ Không tìm thấy Python. Cài Python 3 trước." >&2
    exit 1
fi
