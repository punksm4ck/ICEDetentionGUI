import json, logging, os, sys, math
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QToolBar, QLabel, QPushButton, QFrame, QLineEdit, QSizePolicy)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QIcon
from app.data_store import get_facilities_as_json, get_stats, FACILITIES
from app.chat_sidebar import AIChatSidebar
from app.water_meter import WaterStatusWidget, WaterMeterController

class MainWindow(QMainWindow):
    def __init__(self, app_icon=None):
        super().__init__()
        self.setWindowTitle("ICE DRI Tracker — Logistics Command")
        self.resize(1600, 900)
        self.setStyleSheet("QMainWindow { background: #010409; } QLabel { color: #c9d1d9; font-family: monospace; }")
        self._build_ui()
        self._tick_timestamp()
        QTimer.singleShot(1500, self._add_proximity_alert)

    def _build_ui(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        title = QLabel("  ⬡  ICE ENFORCEMENT TRACKER  ")
        title.setStyleSheet("color: #ff4d4d; font-weight: bold;")
        tb.addWidget(title)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search DRI network..."); self.search.setFixedWidth(250); tb.addWidget(self.search)
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred); tb.addWidget(spacer)
        self.ts_label = QLabel(); tb.addWidget(self.ts_label)
        self.chat_toggle = QPushButton("◧  AI Chat"); self.chat_toggle.setCheckable(True); self.chat_toggle.toggled.connect(self._toggle_chat); tb.addWidget(self.chat_toggle)
        
        container = QWidget(); self.setCentralWidget(container)
        main_layout = QHBoxLayout(container); main_layout.setContentsMargins(0,0,0,0); main_layout.setSpacing(0)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.webview = QWebEngineView()
        self.webview.setMinimumSize(600, 400)
        html_path = Path(__file__).resolve().parent / "map_widget.html"
        self.webview.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.webview.setUrl(QUrl.fromLocalFile(str(html_path)))
        def _inject_data(ok):
            if ok:
                js = f"loadDatacenters({get_facilities_as_json()});"
                QTimer.singleShot(300, lambda: self.webview.page().runJavaScript(js))
        self.webview.loadFinished.connect(_inject_data)
        
        self.chat = AIChatSidebar(); self.chat.setVisible(False); self.chat.words_generated.connect(self._on_words)
        self.splitter.addWidget(self.webview); self.splitter.addWidget(self.chat); self.splitter.setSizes([1200, 400]); main_layout.addWidget(self.splitter)
        
        sb = self.statusBar(); s = get_stats()
        sb.addWidget(QLabel(f"  {s['total']} Facilities  |  Target: {s['total_beds']:,} DRI Beds  "))
        self.water = WaterStatusWidget(); sb.addPermanentWidget(self.water)
        self._water_ctrl = WaterMeterController(panel=None, status=self.water)

    def _add_proximity_alert(self):
        def _dist(la1, lo1, la2, lo2):
            r = 3958.8
            p1, p2 = math.radians(la1), math.radians(la2)
            dla, dlo = math.radians(la2-la1), math.radians(lo2-lo1)
            a = math.sin(dla/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlo/2)**2
            return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        home = (34.2694, -118.7815)
        near = [f for f in FACILITIES if _dist(home[0], home[1], f.lat, f.lng) < 100]
        if near:
            self.statusBar().showMessage(f"⚠ SIMI VALLEY DRI ALERT: {len(near)} facilities within 100 miles (Adelanto, Cal City).", 0)

    def _on_words(self, count):
        if count > 0:
            self._water_ctrl.add_words(count)
        else:
            self._water_ctrl.reset()

    def _toggle_chat(self, on):
        self.chat.setVisible(on); self.splitter.setSizes([1200, 400] if on else [1600, 0])

    def _tick_timestamp(self):
        self.ts_label.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S  "))
        QTimer.singleShot(1000, self._tick_timestamp)
