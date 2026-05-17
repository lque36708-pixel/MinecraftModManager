import sys
from PyQt5.QtWidgets import QApplication

from .theme import DARK_PALETTE, STYLE


_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = QApplication(sys.argv)
        _APP.setStyleSheet(STYLE)
    return _APP


def run():
    from .main_window import MainWindow
    app = get_app()
    w = MainWindow()
    w.showMaximized()
    sys.exit(app.exec_())
