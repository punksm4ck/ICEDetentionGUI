import logging
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QWidget)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

log = logging.getLogger(__name__)

OZ_PER_100_WORDS   = 16.0
CO2_PER_100_WORDS  =  2.0
BOTTLE_FL_OZ       = 16.0
POOL_FL_OZ         = 84535040.0

def _words_in(text: str) -> int:
    import re
    return len(re.findall(r"\b\w+\b", text))

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
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background:rgba(255,77,77,0.12); margin:3px 0;")
        hl.addWidget(sep)
        self._bottle_lbl = _lbl("💧 0 bottles", "#ff7b72")
        self._co2_lbl    = _lbl("🌿 0.00g CO₂", "#44cf7e")
        self._word_lbl   = _lbl("📝 0 words",   "#8b949e")
        for w in (self._bottle_lbl, self._co2_lbl, self._word_lbl):
            hl.addWidget(w)
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
        self._words = 0
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)
        hdr = QLabel("💧  ENFORCEMENT RESOURCE IMPACT")
        hdr.setFont(QFont("Monospace", 9))
        hdr.setStyleSheet("color:rgba(255,77,77,0.70); letter-spacing:1.5px; border-bottom:1px solid rgba(255,77,77,0.15); padding-bottom:6px;")
        root.addWidget(hdr)
        grid = QGridLayout()
        def _metric(icon, label, color):
            ico, lbl, val = QLabel(icon), QLabel(label), QLabel("—")
            ico.setFont(QFont("Monospace", 13))
            lbl.setFont(QFont("Monospace", 8))
            lbl.setStyleSheet("color:rgba(139,148,158,0.70);")
            val.setFont(QFont("Monospace", 12))
            val.setStyleSheet(f"color:{color}; font-weight:bold;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return ico, lbl, val
        i0, l0, self._oz_val    = _metric("💧", "Fluid Ounces",  "#ff7b72")
        i1, l1, self._co2_val   = _metric("🌿", "CO₂ Estimate",  "#44cf7e")
        for row, (ico, lbl, val) in enumerate([(i0,l0,self._oz_val),(i1,l1,self._co2_val)]):
            grid.addWidget(ico, row, 0); grid.addWidget(lbl, row, 1); grid.addWidget(val, row, 2)
        root.addLayout(grid)
    def update_stats(self, words: int, oz: float, co2: float, bottles: float, pool_frac: float):
        self._oz_val.setText(f"{oz:,.2f} oz")
        self._co2_val.setText(f"{co2:,.2f} g")

class WaterMeterController:
    _OZ_PER_WORD   = OZ_PER_100_WORDS  / 100.0
    _CO2_PER_WORD  = CO2_PER_100_WORDS / 100.0
    _POOL_PER_WORD = OZ_PER_100_WORDS  / (100.0 * POOL_FL_OZ)
    _BTL_PER_WORD  = OZ_PER_100_WORDS  / (100.0 * BOTTLE_FL_OZ)
    def __init__(self, panel: WaterMeterPanel, status: WaterStatusWidget):
        self._panel  = panel
        self._status = status
        self._words  = 0
    def add_words(self, n: int):
        if n <= 0: return
        self._words += n
        self._refresh()
    def reset(self):
        self._words = 0
        self._refresh()
    def _refresh(self):
        w   = self._words
        oz, co2, btl, poo = w * self._OZ_PER_WORD, w * self._CO2_PER_WORD, w * self._BTL_PER_WORD, w * self._POOL_PER_WORD
        if self._panel: self._panel.update_stats(w, oz, co2, btl, poo)
        if self._status: self._status.update_stats(w, oz, co2, btl)
