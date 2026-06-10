import sys, os
_d = os.path.dirname(os.path.abspath(__file__))
if _d not in sys.path: sys.path.insert(0, _d)
#!/usr/bin/env python3
"""ICE Detention GUI — entry point."""
import sys, os
# Point at the real app directory
real_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ICEDetentionCenterTracker")
sys.path.insert(0, real_dir)
os.chdir(real_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from app.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ICE DRI Tracker")
    app.setOrganizationName("Punksm4ck")

    icon_path = os.path.join(real_dir, "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
