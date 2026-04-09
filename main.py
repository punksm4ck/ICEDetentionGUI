"© 2026 Punksm4ck. All rights reserved."
"© 2026 Punksm4ck. All rights reserved."
#!/usr/bin/env python3
import logging, os, sys
from pathlib import Path

if "QT_QUICK_BACKEND" in os.environ:
    del os.environ["QT_QUICK_BACKEND"]

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --ignore-gpu-blocklist --enable-gpu-rasterization --enable-webgl --disable-dev-shm-usage"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError as e:
    print(f"Critical Error: {e}"); sys.exit(1)

LOG_DIR = Path.home() / ".local/share/ice-investigative-tracker"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ICE Investigative Tracker")
    from app.main_window import MainWindow
    from app.api_key_manager import ensure_api_key
    window = MainWindow()
    window.show()
    ensure_api_key(parent=window)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
