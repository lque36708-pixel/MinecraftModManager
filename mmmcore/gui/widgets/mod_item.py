from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5 import sip

from ..image import ImageLoader


LOADER_BADGE_STYLES = {
    "fabric":   "color:#89b4fa;",
    "forge":    "color:#fab387;",
    "quilt":    "color:#cba6f7;",
    "neoforge": "color:#f9e2af;",
}


class ModItem(QWidget):
    def __init__(self, data, image_loader, parent=None):
        super().__init__(parent)
        self.data = data
        self.slug = data.get("slug", "")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(12)

        self._icon = QLabel()
        self._icon.setFixedSize(48, 48)
        self._icon.setStyleSheet("background:#363650; border-radius:8px;")
        self._layout.addWidget(self._icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        self._title = QLabel(data.get("title", data.get("slug", "")))
        self._title.setStyleSheet("font-weight:bold; font-size:14px;")
        title_row.addWidget(self._title)

        loaders = data.get("loaders", data.get("categories", []))
        for l in loaders:
            if l in LOADER_BADGE_STYLES:
                badge = QLabel(f"[{l}]")
                badge.setStyleSheet(LOADER_BADGE_STYLES.get(l, "") + "font-size:11px;")
                title_row.addWidget(badge)
        title_row.addStretch()
        text_col.addLayout(title_row)

        desc = data.get("description", "")
        self._desc = QLabel(desc[:120] + ("..." if len(desc) > 120 else ""))
        self._desc.setStyleSheet("color:#a6adc8; font-size:12px;")
        self._desc.setWordWrap(True)
        text_col.addWidget(self._desc)

        meta_parts = []
        dl = data.get("downloads", 0)
        if dl:
            dl_str = f"{dl/1_000_000:.1f}M" if dl >= 1_000_000 else f"{dl/1_000:.1f}K"
            meta_parts.append(f"↓ {dl_str}")
        fw = data.get("follows", 0)
        if fw:
            fw_str = f"{fw/1_000_000:.1f}M" if fw >= 1_000_000 else f"{fw/1_000:.1f}K"
            meta_parts.append(f"♥ {fw_str}")
        cats = [c for c in (data.get("categories") or []) if c not in loaders][:3]
        meta_parts.extend(f"#{c}" for c in cats)
        if meta_parts:
            self._meta = QLabel("  ".join(meta_parts))
            self._meta.setStyleSheet("color:#585b70; font-size:11px;")
            text_col.addWidget(self._meta)

        self._layout.addLayout(text_col, 1)

        if image_loader and data.get("icon_url"):
            image_loader.get(data["icon_url"], self._set_icon)

    def _set_icon(self, pix):
        if not sip.isdeleted(self._icon):
            self._icon.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
