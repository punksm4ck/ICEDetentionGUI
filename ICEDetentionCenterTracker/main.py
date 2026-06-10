import sys, os
_d = os.path.dirname(os.path.abspath(__file__))
if _d not in sys.path: sys.path.insert(0, _d)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
#!/usr/bin/env python3
"""
ICE Detention Center Tracker — USA
Real-time map of detention facilities with Groq AI policy assistant.
"""

import logging
import os
import sys
from pathlib import Path

LOG_DIR = Path.home() / ".local/share/ice-detention-tracker"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s", handlers=[logging.StreamHandler(sys.stderr), logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")])
log = logging.getLogger("main")

ICON_PATH = str(Path.home() / "Pictures/Icons/ICEDetentionTracker.png")

def _check_deps():
    try:
        import PyQt6
        import PyQt6.QtWebEngineWidgets
        import groq
    except ImportError:
        print("ERROR: Missing dependencies. Please run setup.sh")
        sys.exit(0)

def _make_icon(path: str):
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
    from PyQt6.QtCore import Qt
    if Path(path).exists():
        icon = QIcon(path)
        if not icon.isNull(): return icon
    px = QPixmap(64, 64); px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0a1428")); painter.setPen(QColor("#ff5050"))
    painter.drawEllipse(4, 4, 56, 56); painter.end()
    return QIcon(px)

def main():
    _check_deps()
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtCore import Qt
    
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-dev-shm-usage")
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)
    app.setApplicationName("ICE Detention Tracker")
    app.setOrganizationName("AITracker")
    app.setQuitOnLastWindowClosed(False)

    icon = _make_icon(ICON_PATH)
    app.setWindowIcon(icon)

    from app.main_window import MainWindow
    from app.api_key_manager import ensure_api_key

    window = MainWindow(app_icon=icon)

    tray = QSystemTrayIcon(icon, parent=app)
    menu = QMenu()
    menu.setStyleSheet("QMenu { background: #0a0e1a; color: #c0d8f0; font-family: monospace; }")
    act_show = menu.addAction("⬡ Show Tracker")
    act_show.triggered.connect(lambda: (window.showNormal(), window.activateWindow()))
    menu.addAction("✕ Quit").triggered.connect(app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda r: (window.showNormal(), window.activateWindow()) if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    tray.show()

    window.tray_icon = tray; window.show()
    ensure_api_key(parent=window)

    log.info("Application started — PID %d", os.getpid())
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
