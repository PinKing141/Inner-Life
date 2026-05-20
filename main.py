"""Application entry point.

Launches a Qt WebEngine window pointed at ui/index.html, with the Python
GameController exposed to JS via QWebChannel.

Run with:  python main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from bridge import WebBridge
from controller import GameController

UI_PATH = Path(__file__).parent / "ui" / "index.html"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Life — A Deeper Simulation")
        self.resize(440, 820)

        self.controller = GameController()
        self.bridge = WebBridge(self.controller, self)

        self.view = QWebEngineView()
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("bridge", self.bridge)
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
