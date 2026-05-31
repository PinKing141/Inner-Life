"""Application entry point.

Launches a Qt WebEngine window pointed at ui/index.html, with the Python
GameController exposed to JS via QWebChannel.

Run with:  python main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from bridge import WebBridge
from controller import GameController

UI_PATH = Path(__file__).parent / "ui" / "index.html"


class WindowControls(QObject):
    """Exposed to JS as `windowControls`.

    The native OS title bar is removed (frameless window), so the in-app
    titlebar drives minimize / maximize / close / drag through these slots.
    """

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        self._window = window

    @Slot()
    def minimize(self) -> None:
        self._window.showMinimized()

    @Slot()
    def toggleMaximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    @Slot()
    def closeWindow(self) -> None:
        self._window.close()

    @Slot()
    def startDrag(self) -> None:
        handle = self._window.windowHandle()
        if handle is not None:
            handle.startSystemMove()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Life — A Deeper Simulation")
        # Drop the native OS frame; the web UI draws its own titlebar.
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(440, 920)
        self.setMinimumSize(440, 920)

        self.controller = GameController()
        self.bridge = WebBridge(self.controller, self)
        self.window_controls = WindowControls(self)

        self.view = QWebEngineView()
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("bridge", self.bridge)
        self.channel.registerObject("windowControls", self.window_controls)
        self.view.page().setWebChannel(self.channel)

        self.view.load(QUrl.fromLocalFile(str(UI_PATH.resolve())))
        self.setCentralWidget(self.view)


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
