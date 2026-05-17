from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel


def stat_card(value, label):
    frame = QFrame()
    frame.setObjectName("statCard")
    frame.setStyleSheet("""
        QFrame#statCard {
            background:#313244; border-radius:8px;
        }
    """)
    layout = QVBoxLayout(frame)
    layout.setSpacing(2)
    layout.setContentsMargins(8, 8, 8, 8)

    v = QLabel(str(value))
    v.setObjectName("statValue")
    v.setStyleSheet("font-size:18px; font-weight:bold; color:#89b4fa;")
    v.setAlignment(Qt.AlignCenter)

    l = QLabel(label)
    l.setObjectName("statLabel")
    l.setStyleSheet("font-size:11px; color:#a6adc8;")
    l.setAlignment(Qt.AlignCenter)

    layout.addWidget(v)
    layout.addWidget(l)
    return frame
