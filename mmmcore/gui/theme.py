DARK_PALETTE = {
    "bg":        "#1e1e2e",
    "bg2":       "#2a2a3c",
    "bg3":       "#363650",
    "fg":        "#cdd6f4",
    "fg2":       "#a6adc8",
    "accent":    "#89b4fa",
    "green":     "#a6e3a1",
    "red":       "#f38ba8",
    "yellow":    "#f9e2af",
    "orange":    "#fab387",
    "purple":    "#cba6f7",
    "teal":      "#94e2d5",
    "pink":      "#f5c2e7",
    "surface":   "#313244",
    "overlay":   "#45475a",
    "border":    "#585b70",
}

STYLE = """
QMainWindow { background-color: %(bg)s; }
QWidget { color: %(fg)s; font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 13px; }

QLineEdit {
    background: %(bg2)s; border: 1px solid %(border)s; border-radius: 6px;
    padding: 8px 12px; color: %(fg)s; font-size: 14px;
}
QLineEdit:focus { border-color: %(accent)s; }

QComboBox {
    background: %(bg2)s; border: 1px solid %(border)s; border-radius: 6px;
    padding: 6px 10px; color: %(fg)s;
}
QComboBox:hover { border-color: %(accent)s; }
QComboBox::drop-down { border: none; padding-right: 8px; }
QComboBox QAbstractItemView {
    background: %(bg2)s; border: 1px solid %(border)s; color: %(fg)s; selection-background-color: %(accent)s;
}

QPushButton {
    background: %(accent)s; color: %(bg)s; border: none; border-radius: 6px;
    padding: 8px 20px; font-weight: bold; font-size: 13px;
}
QPushButton:hover { background: #9fc5ff; }
QPushButton:pressed { background: #6a9ef5; }
QPushButton:disabled { background: %(overlay)s; color: %(fg2)s; }

QPushButton[secondary="true"] {
    background: transparent; border: 1px solid %(accent)s; color: %(accent)s;
}
QPushButton[secondary="true"]:hover { background: rgba(137,180,250,0.1); }

QPushButton[danger="true"] {
    background: %(red)s; color: %(bg)s;
}
QPushButton[danger="true"]:hover { background: #fca5b5; }

QListWidget {
    background: transparent; border: none; outline: none;
}
QListWidget::item { background: transparent; border-bottom: 1px solid %(border)s; }
QListWidget::item:hover { background: %(bg2)s; }
QListWidget::item:selected { background: %(bg3)s; }

QScrollArea { background: transparent; border: none; }
QScrollBar:vertical {
    background: transparent; width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: %(overlay)s; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: %(border)s; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QTextBrowser { background: transparent; border: none; color: %(fg)s; }

QFrame#statCard {
    background: %(surface)s; border-radius: 8px; padding: 12px;
}
QLabel#statValue { font-size: 18px; font-weight: bold; color: %(accent)s; }
QLabel#statLabel { font-size: 11px; color: %(fg2)s; }

QLabel#sectionTitle { font-size: 14px; font-weight: bold; color: %(teal)s; padding: 8px 0; }

QFrame#sidebar {
    background: %(surface)s; border-right: 1px solid %(border)s;
}
QFrame#sidebarBtn {
    background: transparent; border: none; border-radius: 8px;
    padding: 12px 16px; font-size: 14px; text-align: left;
}
QFrame#sidebarBtn:hover { background: %(bg2)s; }
QFrame#sidebarBtn[active="true"] { background: %(accent)s; color: %(bg)s; }

QProgressBar {
    background: %(bg2)s; border: none; border-radius: 4px; height: 6px; text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 %(accent)s, stop:1 %(teal)s);
    border-radius: 4px;
}
""" % DARK_PALETTE
