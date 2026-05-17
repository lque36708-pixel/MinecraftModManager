from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLabel, QPushButton,
)
from PyQt5.QtCore import QSize

from ..widgets.mod_item import ModItem
from mmmcore.core.state import load_metadata


class ListPage(QWidget):
    def __init__(self, image_loader, parent=None):
        super().__init__(parent)
        self.image_loader = image_loader
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 20, 24, 20)
        self._layout.setSpacing(12)

        header = QHBoxLayout()
        self._title = QLabel("Installed mods")
        self._title.setStyleSheet("font-size:18px; font-weight:bold;")
        header.addWidget(self._title)

        self._info = QLabel()
        self._info.setStyleSheet("color:#a6adc8; font-size:12px;")
        header.addWidget(self._info)

        header.addStretch()
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self._refresh_btn)
        self._layout.addLayout(header)

        self._list = QListWidget()
        self._list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self._layout.addWidget(self._list, 1)

        self.refresh()

    def refresh(self):
        self._list.clear()
        meta = load_metadata()
        mods = meta.get("mods", {})
        count = len(mods)
        total_size = 0

        req = [(s, m) for s, m in mods.items() if m.get("requested")]
        deps = [(s, m) for s, m in mods.items() if not m.get("requested")]

        self._title.setText(f"Installed mods  ({count})")
        self._info.setText("")

        for slug, entry in req + deps:
            total_size += entry.get("size_bytes", 0)
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 72))
            item._slug = slug
            self._list.addItem(item)
            widget = ModItem(entry, self.image_loader)
            self._list.setItemWidget(item, widget)

        if total_size >= 1_000_000:
            size_str = f"{total_size / 1_000_000:.1f} MB"
        else:
            size_str = f"{total_size // 1024:,} KB"
        self._info.setText(f"{count} mod(s)  ·  {size_str}")
