import json
import logging
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QPushButton, QSizePolicy, QSplitter,
    QTableWidget, QTableWidgetItem, QTextEdit, QToolBar, QVBoxLayout, QWidget
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from app.chat_sidebar import AIChatSidebar
from app.data_store import (
    FACILITIES, export_csv, export_geojson, get_facilities_as_json,
    get_stats, sync_live_data
)
from app.water_meter import WaterStatusWidget

log = logging.getLogger("gui")

STYLE = """
QMainWindow { background: #010409; }
QToolBar { background: #0d1117; border-bottom: 1px solid #30363d; padding: 5px; spacing: 6px; }
QStatusBar { background: #0d1117; border-top: 1px solid #30363d; color: #8b949e; font-size: 11px; font-weight: bold; }
QLabel { color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, monospace; }
QPushButton { background: #161b22; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; padding: 5px 10px; font-size: 11px; font-weight: 600; }
QPushButton:hover { background: #21262d; border-color: #00e5ff; }
QPushButton:checked { background: rgba(0, 229, 255, 0.16); color: #00e5ff; border-color: #00e5ff; }
QLineEdit, QComboBox { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #f0f6fc; padding: 4px 8px; font-size: 11px; }
QFrame[objectName="Dashboard"] { background: #0d1117; border-bottom: 1px solid #30363d; }
QFrame[objectName="KpiCard"] { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 4px 10px; }
QTableWidget { background: #0d1117; color: #e6edf3; gridline-color: #21262d; border: none; font-size: 11px; selection-background-color: rgba(255, 106, 0, 0.25); }
QHeaderView::section { background: #161b22; color: #00e5ff; border: 1px solid #21262d; padding: 5px; font-size: 10px; font-weight: bold; }
QTextEdit { background: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; font-size: 11px; padding: 6px; }
.DashLabel { color: #8b949e; font-size: 9px; font-weight: bold; letter-spacing: 1px; }
.DashValue { color: #ffffff; font-size: 18px; font-weight: bold; }
.DashOrange { color: #ff6a00; font-size: 18px; font-weight: bold; }
.DashCyan { color: #00e5ff; font-size: 18px; font-weight: bold; }
.DashDanger { color: #ff4d4d; font-size: 18px; font-weight: bold; }
"""

class SyncWorker(QThread):
    finished = pyqtSignal(bool, str)

    def run(self):
        ok, msg = sync_live_data()
        self.finished.emit(ok, msg)

class MainWindow(QMainWindow):
    def __init__(self, app_icon=None):
        super().__init__()
        self.setWindowTitle("Punksm4ck ICE Intelligence Command — 2026 Edition")
        self.resize(1680, 960)
        self.setStyleSheet(STYLE)
        self.filtered_facilities = list(FACILITIES)
        self.basemap_mode = "dark"
        self.kpi_labels = {}
        self._build_ui()
        self._tick_timestamp()
        QTimer.singleShot(800, self._start_live_sync)

    def _build_ui(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        title = QLabel("  ⬡  ICE INTEL COMMAND  ")
        title.setStyleSheet("color: #ff6a00; font-weight: 800; font-size: 13px;")
        tb.addWidget(title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter city, state, operator, WIRED...")
        self.search.setFixedWidth(230)
        self.search.textChanged.connect(self._apply_filters)
        tb.addWidget(self.search)

        self.state_filter = QComboBox()
        self.state_filter.setFixedWidth(85)
        self.state_filter.addItem("ALL")
        self.state_filter.currentTextChanged.connect(self._apply_filters)
        tb.addWidget(self.state_filter)

        self.cat_buttons = {}
        cat_specs = [
            ("Detention", "DETENTION", True),
            ("Office", "WIRED LEASES", True),
            ("Warehouse", "WAREHOUSES", True),
            ("Staging", "STAGING", True),
            ("Sensitive", "SENSITIVE", False)
        ]
        for key, label, checked in cat_specs:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(checked)
            btn.toggled.connect(self._apply_filters)
            tb.addWidget(btn)
            self.cat_buttons[key] = btn

        self.rings_btn = QPushButton("10-MI RINGS")
        self.rings_btn.setCheckable(True)
        self.rings_btn.toggled.connect(self._apply_filters)
        tb.addWidget(self.rings_btn)

        self.sat_btn = QPushButton("SATELLITE")
        self.sat_btn.setCheckable(True)
        self.sat_btn.toggled.connect(self._toggle_basemap)
        tb.addWidget(self.sat_btn)

        self.sync_btn = QPushButton("↻ SYNC LIVE")
        self.sync_btn.clicked.connect(self._start_live_sync)
        tb.addWidget(self.sync_btn)

        self.export_btn = QPushButton("⬇ EXPORT")
        self.export_btn.clicked.connect(self._export_filtered)
        tb.addWidget(self.export_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self.ts_label = QLabel()
        tb.addWidget(self.ts_label)

        self.chat_toggle = QPushButton("◧ AI CHAT")
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
        dash.setMaximumHeight(74)
        dash_layout = QHBoxLayout(dash)
        dash_layout.setContentsMargins(16, 8, 16, 8)
        dash_layout.setSpacing(12)

        kpi_specs = [
            ("total", "MAPPED NODES", "DashValue"),
            ("national_pop", "NATIONAL POP (TRAC)", "DashOrange"),
            ("non_criminal_pct", "NO CRIMINAL CONVICTION", "DashCyan"),
            ("wired_offices", "WIRED LEASES / HUBS", "DashCyan"),
            ("warehouses", "WAREHOUSES / BUYOUTS", "DashOrange"),
            ("total_deaths", "RECORDED DEATHS", "DashDanger")
        ]
        for key, label_text, css_class in kpi_specs:
            card = QFrame()
            card.setObjectName("KpiCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 3, 8, 3)
            cl.setSpacing(0)
            lbl = QLabel(label_text)
            lbl.setProperty("class", "DashLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val = QLabel("0")
            val.setProperty("class", css_class)
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(lbl)
            cl.addWidget(val)
            dash_layout.addWidget(card)
            self.kpi_labels[key] = val

        main_layout.addWidget(dash)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(6)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["FACILITY", "STATE", "TYPE", "DIST (MI)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        left_layout.addWidget(self.table, stretch=3)

        self.inspector = QTextEdit()
        self.inspector.setReadOnly(True)
        self.inspector.setPlaceholderText("Select any facility to inspect operator, 2026 population, WIRED/Vera source, and proximity telemetry...")
        left_layout.addWidget(self.inspector, stretch=1)

        self.webview = QWebEngineView()
        settings = self.webview.page().settings()
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)

        html_path = Path(__file__).resolve().parent / "map_widget.html"
        self.webview.setHtml(html_path.read_text(encoding="utf-8"), QUrl.fromLocalFile(str(html_path.parent) + "/"))
        self.webview.loadFinished.connect(lambda ok: self._push_data() if ok else None)

        self.chat = AIChatSidebar()
        self.chat.setVisible(False)
        self.chat.words_generated.connect(self._on_words)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(self.webview)
        self.splitter.addWidget(self.chat)
        self.splitter.setSizes([380, 1300, 0])
        main_layout.addWidget(self.splitter)

        sb = self.statusBar()
        self.status_lbl = QLabel("  SYSTEM: Ready  ")
        sb.addWidget(self.status_lbl)
        self.water = WaterStatusWidget()
        sb.addPermanentWidget(self.water)

        self._refresh_state_dropdown()
        self._update_kpis()
        self._populate_table()

    def _start_live_sync(self):
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("↻ SYNCING...")
        self.status_lbl.setText("  SYNC: Pulling Vera Institute live GitHub CSV + 2026 WIRED/TRAC intel...  ")
        self.worker = SyncWorker()
        self.worker.finished.connect(self._on_sync_done)
        self.worker.start()

    def _on_sync_done(self, ok, msg):
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("↻ SYNC LIVE")
        self.status_lbl.setText(f"  {msg}  ")
        self._refresh_state_dropdown()
        self._push_data()
        self._apply_filters()
        self._check_proximity_alert()

    def _refresh_state_dropdown(self):
        current = self.state_filter.currentText()
        states = sorted({f.state for f in FACILITIES if f.state})
        self.state_filter.blockSignals(True)
        self.state_filter.clear()
        self.state_filter.addItem("ALL")
        for st in states:
            self.state_filter.addItem(st)
        idx = self.state_filter.findText(current)
        if idx >= 0:
            self.state_filter.setCurrentIndex(idx)
        self.state_filter.blockSignals(False)

    def _push_data(self):
        self.webview.page().runJavaScript(f"loadDatacenters({get_facilities_as_json()});")
        self._apply_filters()

    def _apply_filters(self):
        q = self.search.text().strip().lower()
        st = self.state_filter.currentText() or "ALL"
        cats = {k: btn.isChecked() for k, btn in self.cat_buttons.items()}
        rings = self.rings_btn.isChecked()

        self.filtered_facilities = []
        for f in FACILITIES:
            if not cats.get(f.category, False):
                continue
            if st != "ALL" and f.state != st:
                continue
            if q:
                hay = f"{f.name} {f.city} {f.state} {f.operator} {f.source} {f.note}".lower()
                if q not in hay:
                    continue
            self.filtered_facilities.append(f)

        self.filtered_facilities.sort(key=lambda x: x.distance_miles())
        self._populate_table()
        self._update_kpis()

        js = f"applyFilters({json.dumps(q)}, {json.dumps(st)}, {json.dumps(cats)}, {str(rings).lower()});"
        self.webview.page().runJavaScript(js)

    def _populate_table(self):
        self.table.setRowCount(len(self.filtered_facilities))
        for row, f in enumerate(self.filtered_facilities):
            name_item = QTableWidgetItem(f.name)
            name_item.setData(Qt.ItemDataRole.UserRole, f.id)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(f.state))
            self.table.setItem(row, 2, QTableWidgetItem(f.category))
            self.table.setItem(row, 3, QTableWidgetItem(f"{f.distance_miles():.1f}"))

    def _on_row_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if idx < 0 or idx >= len(self.filtered_facilities):
            return
        f = self.filtered_facilities[idx]
        self.webview.page().runJavaScript(f"flyToFacility({json.dumps(f.id)});")
        self.inspector.setHtml(
            f"<b style='color:#ff6a00;font-size:13px;'>{f.name}</b><br>"
            f"<span style='color:#00e5ff;'>{f.category} &bull; {f.source}</span><br><br>"
            f"<b>Location:</b> {f.city}, {f.state} ({f.lat:.4f}, {f.lng:.4f})<br>"
            f"<b>Distance from Simi Valley:</b> {f.distance_miles():.1f} mi<br>"
            f"<b>Operator:</b> {f.operator}<br>"
            f"<b>Status:</b> {f.status.upper()}<br>"
            f"<b>Est. Capacity / 2026 ADP:</b> {f.capacity:,} / {f.population:,}<br>"
            f"<b>Recorded Deaths:</b> {f.deaths}<br><br>"
            f"<span style='color:#ffea00;'>{f.note}</span>"
        )

    def _update_kpis(self):
        stats = get_stats(self.filtered_facilities)
        self.kpi_labels["total"].setText(f"{stats['total']:,}")
        self.kpi_labels["national_pop"].setText(f"{stats['national_pop']:,}")
        self.kpi_labels["non_criminal_pct"].setText(f"{stats['non_criminal_pct']}%")
        self.kpi_labels["wired_offices"].setText(str(stats["wired_offices"]))
        self.kpi_labels["warehouses"].setText(str(stats["warehouses"]))
        self.kpi_labels["total_deaths"].setText(str(stats["total_deaths"]))

    def _check_proximity_alert(self):
        near = [f for f in FACILITIES if f.category == "Office" and f.distance_miles() < 75]
        if near:
            near.sort(key=lambda x: x.distance_miles())
            self.statusBar().showMessage(
                f"⚠ SIMI VALLEY PROXIMITY: {len(near)} WIRED expansion hubs within 75 mi (Closest: {near[0].city} at {near[0].distance_miles()} mi).",
                0
            )

    def _toggle_basemap(self, on):
        mode = "satellite" if on else "dark"
        self.webview.page().runJavaScript(f"setBasemap({json.dumps(mode)});")

    def _export_filtered(self):
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Filtered Intelligence",
            str(Path.home() / "Desktop/ice_intel_2026.csv"),
            "CSV File (*.csv);;GeoJSON File (*.geojson)"
        )
        if not path:
            return
        if path.endswith(".geojson") or "GeoJSON" in selected_filter:
            export_geojson(self.filtered_facilities, path)
        else:
            export_csv(self.filtered_facilities, path)
        self.status_lbl.setText(f"  EXPORTED {len(self.filtered_facilities)} nodes to {Path(path).name}  ")

    def _on_words(self, count):
        self.chat._water_ctrl.add_words(count) if count > 0 else self.chat._water_ctrl.reset()

    def _toggle_chat(self, on):
        self.chat.setVisible(on)
        self.splitter.setSizes([360, 960, 360] if on else [380, 1300, 0])

    def _tick_timestamp(self):
        self.ts_label.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S  "))
        QTimer.singleShot(1000, self._tick_timestamp)
