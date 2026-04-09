import logging
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QWidget)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

log = logging.getLogger(__name__)

OZ_PER_100_WORDS   = 16.0
CO2_PER_100_WORDS  =  2.0
BOTTLE_FL_OZ       = 16.0
POOL_FL_OZ         = 84535040.0

class WaterStatusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(6, 0, 6, 0)
        hl.setSpacing(14)
        def _lbl(text, color):
            l = QLabel(text)
            l.setFont(QFont("Monospace", 10))
            l.setStyleSheet(f"color:{color};")
            return l
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background:rgba(255,77,77,0.12); margin:3px 0;")
        hl.addWidget(sep)
        self._bottle_lbl = _lbl("💧 0 bottles", "#00cfff")
        self._co2_lbl    = _lbl("🌿 0.00g CO₂", "#50e878")
        self._word_lbl   = _lbl("📝 0 words",   "#8b949e")
        for w in (self._bottle_lbl, self._co2_lbl, self._word_lbl): hl.addWidget(w)
    def update_stats(self, words: int, oz: float, co2: float, bottles: float):
        self._bottle_lbl.setText(f"💧 {bottles:,.2f} bottles")
        self._co2_lbl.setText(   f"🌿 {co2:,.2f}g CO₂")
        self._word_lbl.setText(  f"📝 {words:,} words")

class WaterMeterPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setStyleSheet("QFrame#waterPanel { background: rgba(1,4,9,0.94); border: 1px solid rgba(255,77,77,0.30); border-radius: 10px; }")
        self.setObjectName("waterPanel")
        self._build()
    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(16, 12, 16, 12); root.setSpacing(10)
        hdr = QLabel("💧  RESOURCES"); hdr.setStyleSheet("color:rgba(0,200,255,0.70); border-bottom:1px solid #333; padding-bottom:6px;")
        root.addWidget(hdr)
        self._oz_val = QLabel("—"); root.addWidget(self._oz_val)
    def update_stats(self, words: int, oz: float, co2: float, bottles: float, pool_frac: float):
        self._oz_val.setText(f"{oz:,.2f} oz")

class WaterMeterController:
    _OZ_PER_WORD = OZ_PER_100_WORDS / 100.0
    _CO2_PER_WORD = CO2_PER_100_WORDS / 100.0
    _POOL_PER_WORD = OZ_PER_100_WORDS / (100.0 * POOL_FL_OZ)
    _BTL_PER_WORD = OZ_PER_100_WORDS / (100.0 * BOTTLE_FL_OZ)
    def __init__(self, panel, status):
        self._panel, self._status, self._words = panel, status, 0
    def add_words(self, n):
        if n > 0: self._words += n; self._refresh()
    def reset(self):
        self._words = 0; self._refresh()
    def _refresh(self):
        w = self._words
        oz, co2, btl, poo = w*self._OZ_PER_WORD, w*self._CO2_PER_WORD, w*self._BTL_PER_WORD, w*self._POOL_PER_WORD
        if self._panel: self._panel.update_stats(w, oz, co2, btl, poo)
        if self._status: self._status.update_stats(w, oz, co2, btl)
