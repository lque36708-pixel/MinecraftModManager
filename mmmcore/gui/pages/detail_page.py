import re
import markdown

from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap, QImage
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QTextBrowser, QProgressBar,
)
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtGui import QTextDocument
from pathlib import Path

from ..workers import ProjectWorker, InstallWorker
from ..widgets.stat_card import stat_card
from ..theme import DARK_PALETTE
from mmmcore.core import (
    get_best_version, get_required_dependencies,
    load_metadata, save_metadata, require_profile,
)
from mmmcore.core.state import remove_mod_from_metadata


INSTALL_STYLE = "background:#89b4fa; color:#1e1e2e;"
UNINSTALL_STYLE = "background:#f38ba8; color:#1e1e2e;"


class DetailTextBrowser(QTextBrowser):
    resource_loaded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._net = QNetworkAccessManager(self)
        self._loading = set()

    def loadResource(self, resource_type, url):
        if resource_type == QTextDocument.ImageResource and url.scheme() in ("http", "https"):
            url_str = url.toString()
            if url_str not in self._loading:
                self._loading.add(url_str)
                reply = self._net.get(QNetworkRequest(QUrl(url_str)))
                reply.finished.connect(lambda r=reply, u=url: self._on_image(r, u))
            pix = QPixmap(1, 1)
            pix.fill(Qt.transparent)
            return pix
        return super().loadResource(resource_type, url)

    def _scale_pixmap(self, pix):
        max_w = int(self.document().textWidth())
        if max_w > 0 and pix.width() > max_w:
            return pix.scaledToWidth(max_w, Qt.SmoothTransformation)
        return pix

    def _on_image(self, reply, url):
        data = reply.readAll()
        if data:
            pix = QPixmap()
            if pix.loadFromData(data):
                pix = self._scale_pixmap(pix)
                self.document().addResource(QTextDocument.ImageResource, url, pix)
            else:
                try:
                    from PIL import Image as PILImage
                    import io
                    pil = PILImage.open(io.BytesIO(bytes(data))).convert("RGBA")
                    qt_img = QImage(pil.tobytes(), pil.width, pil.height, QImage.Format_RGBA8888)
                    pix = QPixmap.fromImage(qt_img)
                    pix = self._scale_pixmap(pix)
                    self.document().addResource(QTextDocument.ImageResource, url, pix)
                except Exception:
                    pass
            tw = self.document().textWidth()
            if tw > 0:
                self.document().setTextWidth(tw)
            self.resource_loaded.emit()


class DetailPage(QWidget):
    def __init__(self, image_loader, parent=None):
        super().__init__(parent)
        self.image_loader = image_loader
        self._slug = ""
        self._installed = False
        self._install_worker = None
        self._body_md = None
        self._last_vp_w = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 16, 24, 16)
        self._layout.setSpacing(0)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(DARK_PALETTE["bg"]))
        self.setPalette(p)

        self._back = QPushButton("← Back")
        self._back.setStyleSheet(
            "background:transparent; border:none; color:#89b4fa; font-size:14px; text-align:left; padding:4px 0;"
        )
        self._layout.addWidget(self._back)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setAutoFillBackground(True)
        p2 = self._scroll.palette()
        p2.setColor(self._scroll.backgroundRole(), QColor(DARK_PALETTE["bg"]))
        self._scroll.setPalette(p2)
        self._scroll.setFrameShape(0)
        self._content = QWidget()
        self._content.setAutoFillBackground(True)
        p3 = self._content.palette()
        p3.setColor(self._content.backgroundRole(), QColor(DARK_PALETTE["bg"]))
        self._content.setPalette(p3)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 12, 0, 20)
        self._content_layout.setSpacing(16)
        self._scroll.setWidget(self._content)
        self._layout.addWidget(self._scroll, 1)

        self._build_content()

    def _build_content(self):
        cl = self._content_layout

        icon_row = QHBoxLayout()
        icon_row.setAlignment(Qt.AlignCenter)
        self._icon = QLabel()
        self._icon.setFixedSize(128, 128)
        self._icon.setStyleSheet("background:#363650; border-radius:16px;")
        icon_row.addWidget(self._icon)
        cl.addLayout(icon_row)

        self._title = QLabel()
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet("font-size:22px; font-weight:bold;")
        cl.addWidget(self._title)

        self._author = QLabel()
        self._author.setAlignment(Qt.AlignCenter)
        self._author.setStyleSheet("color:#a6adc8; font-size:13px;")
        cl.addWidget(self._author)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        self._install_btn = QPushButton("Install")
        self._install_btn.setFixedWidth(250)
        self._install_btn.setStyleSheet("font-size:16px; font-weight:bold; border:none; border-radius:6px; padding:12px 32px;" + INSTALL_STYLE)
        self._install_btn.clicked.connect(self._toggle_install)
        btn_row.addWidget(self._install_btn)
        cl.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(250)
        self._progress.setFixedHeight(6)
        self._progress.hide()
        cl.addWidget(self._progress, alignment=Qt.AlignCenter)

        stat_row = QHBoxLayout()
        stat_row.setSpacing(12)
        self._stat_dl = stat_card("—", "Downloads")
        self._stat_fw = stat_card("—", "Followers")
        self._stat_lc = stat_card("—", "License")
        self._stat_ld = stat_card("—", "Loaders")
        stat_row.addStretch()
        stat_row.addWidget(self._stat_dl)
        stat_row.addWidget(self._stat_fw)
        stat_row.addWidget(self._stat_lc)
        stat_row.addWidget(self._stat_ld)
        stat_row.addStretch()
        cl.addLayout(stat_row)

        self._ver_info = QLabel()
        self._ver_info.setStyleSheet("color:#cdd6f4; font-size:13px;")
        self._ver_info.setWordWrap(True)
        cl.addWidget(self._ver_info)

        self._desc = DetailTextBrowser()
        self._desc.setOpenExternalLinks(True)
        self._desc.setStyleSheet("background:transparent; border:none; color:#cdd6f4; font-size:13px;")
        self._desc.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._desc.resource_loaded.connect(self._stabilize_width)
        cl.addWidget(self._desc)

    def load(self, slug):
        self._slug = slug
        self._installed = False

        self._title.setText("Loading...")
        self._author.setText("")
        self._icon.clear()
        self._install_btn.setText("Install")
        self._install_btn.setStyleSheet("font-size:16px; font-weight:bold; border:none; border-radius:6px; padding:12px 32px;" + INSTALL_STYLE)
        self._install_btn.setEnabled(True)
        self._progress.hide()
        self._ver_info.setText("")
        self._desc.clear()
        self._desc._loading.clear()
        self._body_md = None
        self._last_vp_w = None

        for card in (self._stat_dl, self._stat_fw, self._stat_lc, self._stat_ld):
            labels = card.findChildren(QLabel)
            if len(labels) >= 2:
                labels[0].setText("—")
                labels[1].setText(labels[1].text())

        meta = load_metadata()
        if slug in meta.get("mods", {}):
            self._installed = True
            self._install_btn.setStyleSheet("font-size:16px; font-weight:bold; border:none; border-radius:6px; padding:12px 32px;" + UNINSTALL_STYLE)
            self._install_btn.setText("Uninstall")

        self.show()

        self._worker = ProjectWorker(slug)
        self._worker.finished.connect(self._on_project)
        self._worker.start()

    def _on_project(self, project):
        if not project.get("slug"):
            self._title.setText("Not found")
            return

        self._title.setText(project.get("title", ""))
        author = project.get("author", "")
        self._author.setText(f"by {author}" if author else "")

        if project.get("icon_url"):
            self.image_loader.get(project["icon_url"], self._set_icon)

        self._set_stat(self._stat_dl, project.get("downloads", 0), "Downloads")
        self._set_stat(self._stat_fw, project.get("followers", 0), "Followers")
        lic = (project.get("license") or {}).get("id", "—")
        self._set_stat(self._stat_lc, lic, "License")
        loaders = ", ".join(project.get("loaders", [])[:3]) or "—"
        self._set_stat(self._stat_ld, loaders, "Loaders")

        try:
            profile = require_profile()
            version = get_best_version(self._slug, profile)
        except Exception:
            version = None

        if version:
            vnum = version.get("version_number", "?")
            vtype = version.get("version_type", "?")
            files = version.get("files", [])
            fname = files[0].get("filename", "") if files else ""
            fsize = files[0].get("size", 0) // 1024 if files else 0
            sha = (files[0].get("hashes", {}).get("sha512", "") or "")[:24]
            self._ver_info.setText(
                f"{vnum}  ·  {vtype}  ·  {fsize:,} KB\n"
                f"File: {fname}\n"
                f"SHA-512: {sha}..."
            )
        else:
            self._ver_info.setText("No version matching current profile.")

        self._body_md = project.get("body", "")
        QTimer.singleShot(0, self._render_body)

    def _set_stat(self, card, value, label):
        labels = card.findChildren(QLabel)
        if len(labels) >= 2:
            if isinstance(value, int):
                if value >= 1_000_000:
                    s = f"{value/1_000_000:.1f}M"
                elif value >= 1000:
                    s = f"{value/1_000:.1f}K"
                else:
                    s = str(value)
            else:
                s = str(value)
            labels[0].setText(s)
            labels[1].setText(label)

    def _set_icon(self, pix):
        self._icon.setPixmap(pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _render_body(self):
        if not self._body_md:
            self._desc.clear()
            return
        if self._body_md.strip().startswith("<"):
            html = self._body_md
        else:
            html = markdown.markdown(self._body_md, extensions=["extra"])
        if self._last_vp_w is not None and abs(self._scroll.viewport().width() - self._last_vp_w) < 20:
            return
        self._desc.setHtml(
            f'<html><body style="color:#cdd6f4; font-size:15px; word-wrap:break-word;">{html}</body></html>'
        )
        scroll_w = self._scroll.viewport().width()
        self._last_vp_w = scroll_w
        self._desc.document().setTextWidth(scroll_w)
        h = self._desc.document().size().height()
        if h > 0:
            self._desc.setMinimumHeight(int(h))
            self._desc.setMaximumHeight(int(h))
        QTimer.singleShot(0, self._stabilize_width)

    def _stabilize_width(self):
        vp_w = self._scroll.viewport().width()
        cur_w = self._desc.width()
        if cur_w > vp_w + 3:
            self._desc.setFixedWidth(vp_w)
            self._desc.document().setTextWidth(vp_w)
        self._desc.setMaximumWidth(vp_w)
        h = self._desc.document().size().height()
        if h > 0:
            self._desc.setMinimumHeight(int(h))
            self._desc.setMaximumHeight(int(h))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._body_md is not None:
            self._render_body()

    def _toggle_install(self):
        if self._installed:
            self._uninstall()
        else:
            self._install()

    def _install(self):
        try:
            profile = require_profile()
        except Exception as e:
            self._install_btn.setText(str(e))
            return

        dest_dir = Path.cwd()
        metadata = load_metadata()
        metadata["mc_version"] = profile["mc_version"]
        metadata["loader"] = profile["loader"]

        self._install_btn.setEnabled(False)
        self._install_btn.setText("Installing...")
        self._progress.setValue(0)
        self._progress.show()

        self._install_worker = InstallWorker(self._slug, profile, dest_dir, metadata)
        self._install_worker.progress.connect(self._on_install_progress)
        self._install_worker.done.connect(self._on_install_done)
        self._install_worker.start()

    def _on_install_progress(self, event, data):
        if event == "download_progress":
            self._progress.setValue(data.get("pct", 0))
        elif event in ("download_done", "skip_exists"):
            self._progress.setValue(100)

    def _on_install_done(self, slug, success):
        self._install_btn.setEnabled(True)
        if success:
            save_metadata(self._install_worker.metadata)
            self._installed = True
            self._install_btn.setText("Uninstall")
            self._install_btn.setStyleSheet("font-size:16px; font-weight:bold; border:none; border-radius:6px; padding:12px 32px;" + UNINSTALL_STYLE)
        else:
            self._install_btn.setText("Install (failed)")
            self._install_btn.setStyleSheet("font-size:16px; font-weight:bold; border:none; border-radius:6px; padding:12px 32px;" + INSTALL_STYLE)
        self._progress.hide()

    def _uninstall(self):
        meta = load_metadata()
        mods = meta.get("mods", {})
        entry = mods.get(self._slug, {})
        fname = entry.get("file", "")
        fpath = Path.cwd() / fname if fname else None
        remove_mod_from_metadata(meta, self._slug)
        if fpath and fpath.exists():
            fpath.unlink()
        save_metadata(meta)
        self._installed = False
        self._install_btn.setText("Install")
        self._install_btn.setStyleSheet("font-size:16px; font-weight:bold; border:none; border-radius:6px; padding:12px 32px;" + INSTALL_STYLE)
