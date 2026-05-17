from PyQt5.QtCore import QThread, pyqtSignal

from mmmcore.core import (
    search_mods, get_project, get_best_version,
    install_mod,
)


class SearchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query, mc_version=None, loader=None, no_filter=False, limit=20):
        super().__init__()
        self.query = query
        self.mc_version = mc_version
        self.loader = loader
        self.no_filter = no_filter
        self.limit = limit

    def run(self):
        try:
            results = search_mods(
                self.query,
                mc_version=self.mc_version,
                loader=self.loader,
                no_filter=self.no_filter,
                limit=self.limit,
            )
            self.finished.emit(results or [])
        except Exception as e:
            self.error.emit(str(e))


class ProjectWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, slug):
        super().__init__()
        self.slug = slug

    def run(self):
        try:
            project = get_project(self.slug) or {}
            self.finished.emit(project)
        except Exception:
            self.finished.emit({})


class InstallWorker(QThread):
    progress = pyqtSignal(str, dict)
    done = pyqtSignal(str, bool)

    def __init__(self, name, profile, dest_dir, metadata):
        super().__init__()
        self.name = name
        self.profile = profile
        self.dest_dir = dest_dir
        self.metadata = metadata

    def run(self):
        def cb(event, data):
            if event in ("downloading", "download_progress"):
                self.progress.emit(event, data)
            elif event == "download_done":
                self.progress.emit("download_done", data)
            elif event == "skip_exists":
                self.progress.emit("skip_exists", data)

        try:
            slug = install_mod(
                self.name, self.profile, self.dest_dir,
                self.metadata, status_callback=cb,
            )
            self.done.emit(slug, slug is not None)
        except Exception as e:
            self.done.emit(None, False)
            self.progress.emit("error", {"error": str(e)})
