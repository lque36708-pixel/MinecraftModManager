import hashlib
import io
from pathlib import Path

from PIL import Image

from PyQt5.QtCore import QObject, QByteArray, QUrl, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

CACHE_DIR = Path.home() / ".cache" / "mmm" / "icons"


class ImageLoader(QObject):
    loaded = pyqtSignal(str, QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._pending = {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def get(self, url_str, callback=None):
        if not url_str:
            return
        cache_key = hashlib.md5(url_str.encode()).hexdigest()
        cache_file = CACHE_DIR / cache_key
        if cache_file.exists():
            pix = QPixmap(str(cache_file))
            if not pix.isNull():
                if callback:
                    callback(pix)
                return
        if callback:
            self._pending[url_str] = callback
        reply = self._manager.get(QNetworkRequest(QUrl(url_str)))
        reply.finished.connect(self._on_reply)

    def _on_reply(self):
        reply = self.sender()
        if not reply or reply.error():
            if reply:
                reply.deleteLater()
            return
        url = reply.url().toString()
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_file = CACHE_DIR / cache_key
        data = reply.readAll()
        reply.deleteLater()

        if not data:
            return
        pix = self._decode_image(data)
        if pix and not pix.isNull():
            pix.save(str(cache_file), "PNG")
            cb = self._pending.pop(url, None)
            if cb:
                try:
                    cb(pix)
                except (RuntimeError, TypeError):
                    pass

    def _decode_image(self, data):
        pix = QPixmap()
        buf = QByteArray(data)
        if pix.loadFromData(buf):
            return pix
        try:
            pil_img = Image.open(io.BytesIO(bytes(data)))
            pil_img = pil_img.convert("RGBA")
            qt_img = QImage(
                pil_img.tobytes(),
                pil_img.width,
                pil_img.height,
                QImage.Format_RGBA8888,
            )
            return QPixmap.fromImage(qt_img)
        except Exception:
            return pix
