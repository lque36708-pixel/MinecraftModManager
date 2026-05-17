from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QProgressBar,
)
from PyQt5.QtCore import QThread, pyqtSignal

from ..theme import DARK_PALETTE
from mmmcore.core import (
    load_metadata, save_metadata, remove_mod_from_metadata,
    is_orphaned, require_profile, install_mod,
)
from mmmcore.core.state import load_metadata, save_metadata, remove_mod_from_metadata


class AdvancedPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 20, 24, 20)
        self._layout.setSpacing(16)

        title = QLabel("Advanced")
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        self._layout.addWidget(title)

        # autoremove
        sec_auto = QLabel("Orphaned Dependencies")
        sec_auto.setObjectName("sectionTitle")
        sec_auto.setStyleSheet("font-size:14px; font-weight:bold; color:#94e2d5; padding:8px 0;")
        self._layout.addWidget(sec_auto)

        self._auto_btn = QPushButton("Autoremove orphaned mods")
        self._auto_btn.clicked.connect(self._do_autoremove)
        self._layout.addWidget(self._auto_btn)

        self._auto_result = QLabel()
        self._auto_result.setStyleSheet("color:#a6adc8; font-size:12px;")
        self._layout.addWidget(self._auto_result)

        # install from file
        sec_file = QLabel("Install from File")
        sec_file.setObjectName("sectionTitle")
        sec_file.setStyleSheet("font-size:14px; font-weight:bold; color:#94e2d5; padding:8px 0;")
        self._layout.addWidget(sec_file)

        self._file_btn = QPushButton("Choose .txt file...")
        self._file_btn.clicked.connect(self._install_from_file)
        self._layout.addWidget(self._file_btn)

        # batch install
        sec_batch = QLabel("Batch Install")
        sec_batch.setObjectName("sectionTitle")
        sec_batch.setStyleSheet("font-size:14px; font-weight:bold; color:#94e2d5; padding:8px 0;")
        self._layout.addWidget(sec_batch)

        hint = QLabel("Enter one mod slug per line:")
        hint.setStyleSheet("color:#a6adc8; font-size:12px;")
        self._layout.addWidget(hint)

        self._batch_input = QTextEdit()
        self._batch_input.setPlaceholderText("sodium\nlithium\niris\nferritecore")
        self._batch_input.setMaximumHeight(140)
        self._batch_input.setStyleSheet("background:#2a2a3c; border:1px solid #585b70; border-radius:6px; padding:8px; color:#cdd6f4;")
        self._layout.addWidget(self._batch_input)

        btn_row = QHBoxLayout()
        self._batch_btn = QPushButton("Install All")
        self._batch_btn.clicked.connect(self._do_batch)
        btn_row.addWidget(self._batch_btn)

        self._batch_progress = QProgressBar()
        self._batch_progress.hide()
        btn_row.addWidget(self._batch_progress, 1)
        self._layout.addLayout(btn_row)

        self._batch_list = QListWidget()
        self._batch_list.setMaximumHeight(200)
        self._layout.addWidget(self._batch_list, 1)

        self._layout.addStretch()

    def _do_autoremove(self):
        meta = load_metadata()
        mods = meta.get("mods", {})
        if not mods:
            self._auto_result.setText("No mods in metadata.")
            return
        orphaned = [s for s in mods if is_orphaned(s, mods)]
        if not orphaned:
            self._auto_result.setText("No orphaned dependencies found.")
            return
        dest = __import__("pathlib").Path.cwd()
        removed = 0
        for slug in orphaned:
            entry = mods.get(slug, {})
            fpath = dest / entry["file"] if entry.get("file") else None
            remove_mod_from_metadata(meta, slug)
            if fpath and fpath.exists():
                fpath.unlink()
            removed += 1
        save_metadata(meta)
        self._auto_result.setText(f"Removed {removed} orphaned dep(s).")

    def _install_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select mod list file", "", "Text files (*.txt);;All files (*)"
        )
        if not path:
            return
        with open(path) as f:
            mods = [s.strip() for s in f.read().replace(",", "\n").split("\n") if s.strip()]
        if mods:
            self._batch_input.setText("\n".join(mods))
            QMessageBox.information(self, "File loaded", f"Loaded {len(mods)} mod(s). Click 'Install All'.")

    def _do_batch(self):
        lines = self._batch_input.toPlainText().strip()
        if not lines:
            return
        mods = [s.strip() for s in lines.replace(",", "\n").split("\n") if s.strip()]
        if not mods:
            return

        try:
            profile = require_profile()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        dest_dir = __import__("pathlib").Path.cwd()
        metadata = load_metadata()
        metadata["mc_version"] = profile["mc_version"]
        metadata["loader"] = profile["loader"]

        self._batch_btn.setEnabled(False)
        self._batch_progress.setMaximum(len(mods))
        self._batch_progress.setValue(0)
        self._batch_progress.show()
        self._batch_list.clear()

        self._batch_worker = _BatchWorker(mods, profile, dest_dir, metadata)
        self._batch_worker.item_done.connect(self._on_batch_item)
        self._batch_worker.all_done.connect(self._on_batch_done)
        self._batch_worker.start()

    def _on_batch_item(self, name, slug, success, msg):
        count = self._batch_progress.value() + 1
        self._batch_progress.setValue(count)
        item = QListWidgetItem(f"{'✔' if success else '✗'} {name}  →  {slug if success else msg}")
        item.setStyleSheet(f"color:{'#a6e3a1' if success else '#f38ba8'};")
        self._batch_list.addItem(item)

    def _on_batch_done(self):
        self._batch_btn.setEnabled(True)
        self._batch_progress.hide()


class _BatchWorker(QThread):
    item_done = pyqtSignal(str, str, bool, str)
    all_done = pyqtSignal()

    def __init__(self, mods, profile, dest_dir, metadata):
        super().__init__()
        self.mods = mods
        self.profile = profile
        self.dest_dir = dest_dir
        self.metadata = metadata

    def run(self):
        for name in self.mods:
            try:
                slug = install_mod(name, self.profile, self.dest_dir, self.metadata)
                if slug:
                    self.item_done.emit(name, slug, True, "")
                else:
                    self.item_done.emit(name, name, False, "not found")
            except Exception as e:
                self.item_done.emit(name, name, False, str(e))
        save_metadata(self.metadata)
        self.all_done.emit()
