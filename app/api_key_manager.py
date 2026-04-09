import base64
import hashlib
import logging
import os
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

log = logging.getLogger(__name__)

KEY_DIR  = Path.home() / ".local/share/ice-investigative-tracker"
KEY_FILE = KEY_DIR / "groq_key.enc"

def _secret() -> bytes:
    mid = ""
    p = Path("/etc/machine-id")
    if p.exists(): mid = p.read_text().strip()
    return hashlib.sha256((mid + "ice-investigative-groq").encode()).digest()

def _encrypt(text: str) -> bytes:
    data, s = text.encode(), _secret()
    return base64.b64encode(b"XOR:" + bytes(b ^ s[i % 32] for i, b in enumerate(data)))

def _decrypt(blob: bytes) -> str:
    try:
        raw = base64.b64decode(blob)
        if raw.startswith(b"XOR:"):
            s, data = _secret(), raw[4:]
            return bytes(b ^ s[i % 32] for i, b in enumerate(data)).decode()
    except Exception: pass
    return ""

def load_api_key() -> str:
    env = os.environ.get("GROQ_API_KEY", "").strip()
    if env: return env
    if KEY_FILE.exists():
        k = _decrypt(KEY_FILE.read_bytes())
        if k: return k
    return ""

def save_api_key(key: str):
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_bytes(_encrypt(key))
    KEY_FILE.chmod(0o600)

def apply_to_env(key: str):
    os.environ["GROQ_API_KEY"] = key

class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Groq API Access — Investigative Tracker")
        self.setFixedWidth(400)
        self.setStyleSheet("QDialog { background: #0d1117; } QLabel { color: #c9d1d9; font-family: monospace; } QLineEdit { background: #161b22; border: 1px solid #30363d; color: #c9d1d9; padding: 5px; }")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("ENTER GROQ API KEY:"))
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.input)
        btn = QPushButton("SAVE KEY")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
    def get_key(self): return self.input.text().strip()

def ensure_api_key(parent=None) -> str:
    key = load_api_key()
    if key:
        apply_to_env(key)
        return key
    dlg = ApiKeyDialog(parent)
    if dlg.exec():
        k = dlg.get_key()
        save_api_key(k)
        apply_to_env(k)
        return k
    return ""

def prompt_reauth(parent=None):
    if KEY_FILE.exists(): KEY_FILE.unlink()
    return ensure_api_key(parent)
