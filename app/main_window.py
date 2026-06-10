import json, logging, os, sys, math
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QToolBar, QLabel, QPushButton, QLineEdit, QSizePolicy, QFrame)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QIcon
from app.data_store import get_facilities_as_json, get_stats, FACILITIES
from app.chat_sidebar import AIChatSidebar
from app.water_meter import WaterStatusWidget

log = logging.getLogger("gui")

STYLE = """
QMainWindow { background: #010409; }
QToolBar { background: #0d1117; border-bottom: 1px solid #30363d; padding: 4px; }
QStatusBar { background: #0d1117; border-top: 1px solid #30363d; color: #8b949e; font-size: 11px; font-weight: bold; }
QLabel { color: #c9d1d9; font-family: monospace; }
QPushButton { background: #21262d; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; padding: 5px 15px; }
QPushButton:hover { background: #30363d; }
QLineEdit { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; padding: 4px; }
QFrame[objectName="Dashboard"] { background: #0d1117; border-bottom: 1px solid #30363d; }
.DashLabel { color: #8b949e; font-size: 10px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; }
.DashValue { color: #ffffff; font-size: 22px; font-weight: bold; }
.DashDanger { color: #ff4d4d; font-size: 22px; font-weight: bold; }
.DashWarn { color: #ffea00; font-size: 22px; font-weight: bold; }
"""

class MainWindow(QMainWindow):
    def __init__(self, app_icon=None):
        super().__init__()
        self.setWindowTitle("ICE DRI Tracker — Logistics Command")
        self.resize(1600, 900)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._tick_timestamp()
        QTimer.singleShot(2000, self._add_proximity_alert)

    def _build_ui(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        title = QLabel("  ⬡  ICE ENFORCEMENT TRACKER  ")
        title.setStyleSheet("color: #ff4d4d; font-weight: bold;")
        tb.addWidget(title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search network...")
        self.search.setFixedWidth(250)
        tb.addWidget(self.search)

        self.refresh_btn = QPushButton("↻  RELOAD MAP")
        self.refresh_btn.clicked.connect(self._push_data)
        tb.addWidget(self.refresh_btn)

        self.sens_btn = QPushButton("⚠ SENSITIVE PROXIMITY")
        self.sens_btn.setCheckable(True)
        self.sens_btn.setStyleSheet("QPushButton:checked { background: rgba(0, 224, 255, 0.2); color: #00e0ff; border-color: #00e0ff; }")
        self.sens_btn.toggled.connect(lambda on: self.webview.page().runJavaScript(f"toggleSensitive({str(on).lower()});"))
        tb.addWidget(self.sens_btn)

        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self.ts_label = QLabel()
        tb.addWidget(self.ts_label)

        self.chat_toggle = QPushButton("◧  AI Chat")
        self.chat_toggle.setCheckable(True)
        self.chat_toggle.toggled.connect(self._toggle_chat)
        tb.addWidget(self.chat_toggle)

        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        dash = QFrame()
        dash.setObjectName("Dashboard")
        dash.setMaximumHeight(65)
        dash_layout = QHBoxLayout(dash)
        dash_layout.setContentsMargins(30, 5, 30, 5)

        stats = get_stats()

        metrics = [
            ("NETWORK NODES", str(stats["total"]), "DashValue"),
            ("ESTIMATED CAPACITY", f"{stats['total_beds']:,}", "DashValue"),
            ("VERIFIED POPULATION", f"{stats['total_pop']:,}", "DashValue"),
            ("RECORDED DEATHS", str(stats["total_deaths"]), "DashDanger"),
            ("REPORTED PREGNANCIES", str(stats["total_pregs"]), "DashWarn")
        ]

        dash_layout.addStretch()
        for label_text, val_text, val_class in metrics:
            block = QVBoxLayout()
            block.setSpacing(0)
            lbl = QLabel(label_text)
            lbl.setProperty("class", "DashLabel")
            val = QLabel(val_text)
            val.setProperty("class", val_class)
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            block.addWidget(lbl)
            block.addWidget(val)
            dash_layout.addLayout(block)
            dash_layout.addStretch()

        main_layout.addWidget(dash)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.webview = QWebEngineView()
        self.webview.page().javaScriptConsoleMessage = self._on_js_console

        settings = self.webview.page().settings()
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)

        html_path = Path(__file__).resolve().parent / "map_widget.html"
        html_content = html_path.read_text(encoding="utf-8")
        self.webview.setHtml(html_content, QUrl.fromLocalFile(str(html_path.parent) + "/"))
        self.webview.loadFinished.connect(lambda ok: self._push_data() if ok else None)

        self.chat = AIChatSidebar()
        self.chat.setVisible(False)
        self.chat.words_generated.connect(self._on_words)

        self.splitter.addWidget(self.webview)
        self.splitter.addWidget(self.chat)
        self.splitter.setSizes([1600, 0])
        main_layout.addWidget(self.splitter)

        sb = self.statusBar()
        sb.addWidget(QLabel("  SYSTEM: Live Telemetry Engine Active. Automatically polling for external API data sync.  "))
        self.water = WaterStatusWidget()
        sb.addPermanentWidget(self.water)

    def _on_js_console(self, level, message, line, source):
        log.info(f"JS Console [{level}]: {message} (Line: {line})")

    def _push_data(self):
        self.webview.page().runJavaScript(f"loadDatacenters({get_facilities_as_json()});")

    def _add_proximity_alert(self):
        def _dist(lat1, lon1, lat2, lo2):
            r = 3958.8
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi, dlam = math.radians(lat2-lat1), math.radians(lo2-lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
            return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        home = (34.2694, -118.7815)
        near = [f for f in FACILITIES if f.category == "Office" and _dist(home[0], home[1], f.lat, f.lng) < 100]
        if near:
            self.statusBar().showMessage(f"⚠ SIMI VALLEY SURGE ALERT: Secret expansion office detected in {near[0].city}.", 0)

    def _on_words(self, count):
        self.chat._water_ctrl.add_words(count) if count > 0 else self.chat._water_ctrl.reset()

    def _toggle_chat(self, on):
        self.chat.setVisible(on)
        self.splitter.setSizes([1200, 400] if on else [1600, 0])

    def _tick_timestamp(self):
        self.ts_label.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S  "))
        QTimer.singleShot(1000, self._tick_timestamp)
