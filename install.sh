
#!/usr/bin/env bash
set -e

# ─── Colors ───────────────────────────────────────────────────────────────────
G="\033[32m"; Y="\033[33m"; C="\033[36m"; BOLD="\033[1m"; R="\033[0m"; RED="\033[31m"
ok()   { echo -e "${G}✓ $*${R}"; }
info() { echo -e "${C}→ $*${R}"; }
err()  { echo -e "${RED}✗ $*${R}" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASHRC="$HOME/.bashrc"
MARKER="# 3m-minecraft-mod-manager"

echo -e "\n${BOLD}3m — Minecraft Mod Manager${R}"
echo -e "${C}────────────────────────────────${R}\n"

# ─── Kiểm tra Python ──────────────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PY=$(command -v python3)
    ok "Python3 tìm thấy: $PY"
else
    err "Không tìm thấy python3. Cài Python 3 trước."
fi

# ─── Kiểm tra file ────────────────────────────────────────────────────────────
[[ -f "$SCRIPT_DIR/3m.py" ]] || err "Không tìm thấy 3m.py trong $SCRIPT_DIR"
[[ -f "$SCRIPT_DIR/3m.sh" ]] || err "Không tìm thấy 3m.sh trong $SCRIPT_DIR"

# ─── Chmod ────────────────────────────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/3m.sh" "$SCRIPT_DIR/3m.py"
ok "Đã chmod +x"

# ─── Kiểm tra đã cài chưa ────────────────────────────────────────────────────
if grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
    echo -e "${Y}! 3m đã được thêm vào $BASHRC rồi.${R}"
    # Cập nhật path nếu thư mục khác
    OLD_LINE=$(grep -A1 "$MARKER" "$BASHRC" | tail -1)
    OLD_PATH=$(echo "$OLD_LINE" | grep -oP '(?<=alias 3m=")[^"]+' || true)
    if [[ "$OLD_PATH" != "$SCRIPT_DIR/3m.sh" ]]; then
        info "Cập nhật path mới: $SCRIPT_DIR/3m.sh"
        # Xóa block cũ
        sed -i "/$MARKER/,+1d" "$BASHRC"
    else
        ok "Path không đổi, bỏ qua."
        echo -e "\n${BOLD}Chạy lệnh sau để dùng ngay:${R}"
        echo -e "  source ~/.bashrc\n"
        exit 0
    fi
fi

# ─── Thêm vào .bashrc ─────────────────────────────────────────────────────────
cat >> "$BASHRC" <<EOF

$MARKER
alias 3m="$SCRIPT_DIR/3m.sh"
EOF

ok "Đã thêm alias vào $BASHRC"

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
ok "Cài đặt hoàn tất!"
echo -e "\n${BOLD}Chạy lệnh sau để dùng ngay (hoặc mở terminal mới):${R}"
echo -e "  ${C}source ~/.bashrc${R}"
echo -e "\n${BOLD}Bắt đầu:${R}"
echo -e "  ${C}3m set-profile 1.21.1 fabric${R}"
echo -e "  ${C}3m search sodium${R}"
echo ""