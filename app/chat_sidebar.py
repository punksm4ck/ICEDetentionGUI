import json
import logging
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from app.data_store import get_stats
from app.water_meter import WaterMeterPanel, WaterMeterController

log = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a Doctorate-level ICE Surge Logistics Analyst embedded in the Investigative Tracker.
Expertise:
• Federal Procurement & GSA Leases: Specifically the "Unusual or Compelling Urgency" statute used to bypass open bidding.
• Surge Logistics: The deployment of 13,000 new employees and 250+ new locations under the "One Big Beautiful Bill" initiative.
• Sensitive Proximity Analysis: Tracking OPLA/ERO office expansions near schools, childcare centers, and places of worship.
• Enforcement Infrastructure: Differentiating between high-capacity DRI Mega Centers and street-level surge offices.

Context:
- 150+ secret leases/expansions are underway in nearly every state.
- DHS has asked GSA to hide lease listings due to "national security concerns."
- ICE field offices are expanding from 25 to a nationwide footprint.

Maintain a data-driven, analytical, and objective investigative tone. Cite specific locations from the article (Irvine, The Woodlands, Roseland, etc.) when relevant."""

def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))

class _StreamWorker(QThread):
    chunk = pyqtSignal(str)
    done  = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, messages: list, parent=None):
        super().__init__(parent)
        self._messages = messages

    def run(self):
        try:
            from groq import Groq
            import os
            key = os.environ.get("GROQ_API_KEY", "")
            if not key:
                self.error.emit("__REAUTH__")
                return
            client = Groq(api_key=key)
            stats  = get_stats()
            system = SYSTEM_PROMPT + f"\n\nLive investigative stats: {json.dumps(stats)}"

            with client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"system","content":system}] + self._messages,
                max_tokens=1024,
                stream=True,
            ) as stream:
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        self.chunk.emit(delta)
            self.done.emit()
        except Exception as exc:
            self.error.emit(str(exc))

class _Bubble(QFrame):
    def __init__(self, text: str, role: str):
        super().__init__()
        lay = QVBoxLayout(self)
        self.body = QLabel(text)
        self.body.setWordWrap(True)
        self.body.setFont(QFont("Monospace", 9))
        self.body.setStyleSheet("color:#d0e8ff; line-height:1.4;")
        lay.addWidget(self.body)
        color = "rgba(40,80,140,0.35)" if role == "user" else "rgba(60,30,100,0.30)"
        self.setStyleSheet(f"QFrame{{background:{color}; border:1px solid rgba(255,77,77,0.20); border-radius:8px; margin:2px;}}")

class AIChatSidebar(QWidget):
    words_generated = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(350)
        self._history = []
        self._worker = None
        self._live_bubble = None
        self._live_text = ""
        self._build()

    def _build(self):
        self.setStyleSheet("background:rgba(13,17,23,0.98); border-left: 1px solid #30363d;")
        root = QVBoxLayout(self)

        hdr = QLabel("SURGE LOGISTICS ASSISTANT")
        hdr.setStyleSheet("color:#ff4d4d; font-weight:bold; padding:10px; border-bottom:1px solid #30363d;")
        root.addWidget(hdr)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._msg_widget = QWidget()
        self._msg_layout = QVBoxLayout(self._msg_widget)
        self._msg_layout.addStretch()
        self._scroll.setWidget(self._msg_widget)
        root.addWidget(self._scroll)

        self._input = QTextEdit()
        self._input.setPlaceholderText("Query the surge expansion...")
        self._input.setFixedHeight(80)
        self._input.setStyleSheet("background:#161b22; color:#c9d1d9; border:1px solid #30363d; border-radius:5px;")
        root.addWidget(self._input)

        self._send_btn = QPushButton("EXECUTE ANALYTICAL QUERY")
        self._send_btn.clicked.connect(self._on_send)
        root.addWidget(self._send_btn)

        self.water_panel = WaterMeterPanel()
        self._water_ctrl = WaterMeterController(panel=self.water_panel, status=None)

    def _on_send(self):
        text = self._input.toPlainText().strip()
        if not text or (self._worker and self._worker.isRunning()): return
        self._add_bubble(text, "user")
        self._history.append({"role":"user", "content":text})
        self._input.clear()
        self._live_text = ""
        self._live_bubble = self._add_bubble("...", "assistant")
        self._worker = _StreamWorker(list(self._history))
        self._worker.chunk.connect(self._on_chunk)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_chunk(self, t):
        old = _count_words(self._live_text)
        self._live_text += t
        delta = _count_words(self._live_text) - old
        if delta > 0: self.words_generated.emit(delta)
        if self._live_bubble: self._live_bubble.body.setText(self._live_text)

    def _on_done(self):
        self._history.append({"role":"assistant", "content":self._live_text})

    def _add_bubble(self, text, role):
        b = _Bubble(text, role)
        self._msg_layout.insertWidget(self._msg_layout.count()-1, b)
        return b
