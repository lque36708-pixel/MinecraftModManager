from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame, QLabel, QStackedWidget, QPushButton,
)

from ..core import load_profile, require_profile
from .image import ImageLoader
from .pages.search_page import SearchPage
from .pages.list_page import ListPage
from .pages.detail_page import DetailPage
from .pages.advanced_page import AdvancedPage
from .theme import DARK_PALETTE, STYLE


PAGE_NAMES = ["search", "list", "detail", "advanced"]

SIDEBAR_BTN = """
QPushButton {
    background: transparent; border: none; border-radius: 8px;
    padding: 12px 16px; font-size: 14px; text-align: left; color: %(fg)s;
}
QPushButton:hover { background: %(bg2)s; }
""" % DARK_PALETTE

SIDEBAR_ACTIVE = """
QPushButton {
    background: %(accent)s; border: none; border-radius: 8px;
    padding: 12px 16px; font-size: 14px; text-align: left; color: %(bg)s;
    font-weight: bold;
}
""" % DARK_PALETTE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mmm — Minecraft Mod Manager")
        self.resize(960, 680)
        self.setStyleSheet(STYLE)

        self.image_loader = ImageLoader(self)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sidebar
        self._sidebar = QFrame()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(8, 16, 8, 16)
        sidebar_layout.setSpacing(4)

        sidebar_layout.addWidget(QLabel("mmm"), 0, Qt.AlignCenter)
        sidebar_layout.addSpacing(16)

        self._nav_buttons = {}
        nav_items = [
            ("search",  "🔍  Search"),
            ("list",    "📋  List"),
            ("advanced","⚙  Advanced"),
        ]
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._switch_page(k))
            self._nav_buttons[key] = btn
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        self._profile_label = QLabel()
        self._profile_label.setStyleSheet(f"color:{DARK_PALETTE['fg2']}; font-size:11px; padding:8px;")
        sidebar_layout.addWidget(self._profile_label)

        root.addWidget(self._sidebar)

        # stack
        self._stack = QStackedWidget()
        self._search_page = SearchPage(self.image_loader, self._get_profile)
        self._list_page = ListPage(self.image_loader)
        self._detail_page = DetailPage(self.image_loader)
        self._advanced_page = AdvancedPage()

        self._stack.addWidget(self._search_page)
        self._stack.addWidget(self._list_page)
        self._stack.addWidget(self._detail_page)
        self._stack.addWidget(self._advanced_page)

        root.addWidget(self._stack, 1)

        # signals — single connection, no duplicates
        self._search_page._list.itemClicked.connect(self._on_search_click)
        self._list_page._list.itemClicked.connect(self._on_list_click)
        self._detail_page._back.clicked.connect(self._back_from_detail)

        self._update_profile_display()
        self._switch_page("search")

    def _get_profile(self):
        try:
            return require_profile()
        except Exception:
            return None

    def _update_profile_display(self):
        p = load_profile()
        if p:
            self._profile_label.setText(
                f"MC: {p['mc_version']}\nLoader: {p['loader']}"
            )
        else:
            self._profile_label.setText("No profile set")

    def _switch_page(self, key):
        for k, btn in self._nav_buttons.items():
            btn.setStyleSheet(SIDEBAR_ACTIVE if k == key else SIDEBAR_BTN)
        idx = PAGE_NAMES.index(key)
        self._stack.setCurrentIndex(idx)

    def _on_search_click(self, item):
        slug = getattr(item, "_slug", "")
        if slug:
            self._open_detail(slug, "search")

    def _on_list_click(self, item):
        slug = getattr(item, "_slug", "")
        if slug:
            self._open_detail(slug, "list")

    def _open_detail(self, slug, source):
        self._detail_page._source_page = source
        self._detail_page.load(slug)
        idx = PAGE_NAMES.index("detail")
        self._stack.setCurrentIndex(idx)

    def _back_from_detail(self):
        source = getattr(self._detail_page, "_source_page", "search")
        self._switch_page(source)
