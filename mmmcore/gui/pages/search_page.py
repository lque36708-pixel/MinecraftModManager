from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QCheckBox,
)

from ..workers import SearchWorker
from ..widgets.mod_item import ModItem
from ..theme import DARK_PALETTE


class SearchPage(QWidget):
    def __init__(self, image_loader, profile_manager, parent=None):
        super().__init__(parent)
        self.image_loader = image_loader
        self.get_profile = profile_manager
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 20, 24, 20)
        self._layout.setSpacing(12)

        search_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Search mods on Modrinth...")
        self._input.returnPressed.connect(self._do_search)
        search_row.addWidget(self._input, 1)

        self._btn = QPushButton("Search")
        self._btn.clicked.connect(self._do_search)
        search_row.addWidget(self._btn)
        self._layout.addLayout(search_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        profile = self.get_profile()

        self._mc = QComboBox()
        self._mc.setEditable(True)
        if profile:
            self._mc.addItem(profile["mc_version"])
        self._mc.addItems([
            "1.21.4", "1.21.3", "1.21.1", "1.21", "1.20.6", "1.20.4",
            "1.20.1", "1.19.4", "1.18.2",
        ])
        self._mc.setCurrentIndex(0)
        filter_row.addWidget(QLabel("MC:"))
        filter_row.addWidget(self._mc)

        self._loader = QComboBox()
        self._loader.addItems(["fabric", "forge", "neoforge", "quilt"])
        if profile:
            self._loader.setCurrentText(profile["loader"])
        filter_row.addWidget(QLabel("Loader:"))
        filter_row.addWidget(self._loader)

        self._no_filter = QCheckBox("All versions / loaders")
        filter_row.addWidget(self._no_filter)
        filter_row.addStretch()
        self._layout.addLayout(filter_row)

        self._count_label = QLabel()
        self._count_label.setStyleSheet("color:#a6adc8; font-size:12px;")
        self._layout.addWidget(self._count_label)

        self._list = QListWidget()
        self._list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self._layout.addWidget(self._list, 1)

        if profile:
            self._do_search()

    def _do_search(self):
        query = self._input.text().strip()
        if not query:
            return
        self._btn.setEnabled(False)
        self._btn.setText("Searching...")
        self._list.clear()
        self._count_label.setText("")

        profile = self.get_profile()
        mc = None if self._no_filter.isChecked() else (self._mc.currentText() or (profile and profile.get("mc_version")))
        loader = None if self._no_filter.isChecked() else (self._loader.currentText() or (profile and profile.get("loader")))

        self._worker = SearchWorker(query, mc_version=mc, loader=loader,
                                     no_filter=self._no_filter.isChecked())
        self._worker.finished.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_results(self, results):
        self._list.clear()
        self._count_label.setText(f"{len(results)} result(s)")
        for r in results:
            slug = r.get("slug", "")
            loaders = [l for l in (r.get("categories") or []) if l in ("fabric", "forge", "neoforge", "quilt")]
            r["loaders"] = loaders
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 72))
            item._slug = slug
            self._list.addItem(item)
            widget = ModItem(r, self.image_loader)
            self._list.setItemWidget(item, widget)
        self._btn.setEnabled(True)
        self._btn.setText("Search")

    def _on_error(self, msg):
        self._count_label.setText(f"Error: {msg}")
        self._btn.setEnabled(True)
        self._btn.setText("Search")
