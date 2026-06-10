import json
import logging
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from app.data_store import get_stats

log = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"
SYSTEM_PROMPT = """You are a Doctorate-level Logistics Analyst for the ICE Detention Center Tracker.
Operational Context:
- There are currently ~265 facilities utilized for immigration detention.
- The "Hub and Spoke" model is transitioning the system to 34 massive, government-owned "mega centers".
- Daily detainee populations have hit record levels between 66,000 and 73,000.
- Funding through 2029 is estimated at $45 billion for infrastructure expansion.

Expertise: Federal Procurement (IGSA), Private Prison REITs (GEO Group, CoreCivic), and Mega-Center logistics.
Maintain a precise, analytical, and enterprise-grade tone."""

def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))

class _StreamWorker(QThread):
    chunk = pyqtSignal(str)
    done  = pyqtSignal()
    error = pyqtSignal(str)
    def __init__(self, messages: list):
        super().__init__()
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
            system = SYSTEM_PROMPT + f"\n\nLive Stats: {json.dumps(get_stats())}"
            with client.chat.completions.create(model=MODEL, messages=[{"role":"system","content":system}] + self._messages, stream=True) as stream:
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta: self.chunk.emit(delta)
            self.done.emit()
        except Exception as e: self.error.emit(str(e))

class _Bubble(QFrame):
    def __init__(self, text: str, role: str):
        super().__init__()
        lay = QVBoxLayout(self)
        self.body = QLabel(text)
        self.body.setWordWrap(True)
        self.body.setStyleSheet("color:#d0e8ff; font-family:monospace; font-size:9px;")
        lay.addWidget(self.body)
        color = "rgba(40,80,140,0.35)" if role == "user" else "rgba(60,30,100,0.30)"
        self.setStyleSheet(f"QFrame{{background:{color}; border:1px solid rgba(255,77,77,0.2); border-radius:8px;}}")

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
        self.setStyleSheet("background:#0d1117; border-left:1px solid #30363d;")
        root = QVBoxLayout(self)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._msg_widget = QWidget()
        self._msg_layout = QVBoxLayout(self._msg_widget)
        self._msg_layout.addStretch()
        self._scroll.setWidget(self._msg_widget)
        root.addWidget(self._scroll)
        self._input = QTextEdit()
        self._input.setFixedHeight(80)
        self._input.setStyleSheet("background:#161b22; color:#c9d1d9; border:1px solid #30363d;")
        root.addWidget(self._input)
        self._send_btn = QPushButton("EXECUTE ANALYTICAL QUERY")
        self._send_btn.clicked.connect(self._send)
        root.addWidget(self._send_btn)
    def _send(self):
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
