"© 2026 Punksm4ck. All rights reserved."
#!/bin/bash
echo " Setting up ICE Detention Center Tracker            "
echo "===================================================="
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed."
    exit 1
fi
if command -v apt-get &> /dev/null; then
    echo "Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y python3-pyqt6 python3-pyqt6.qtwebengine
fi
echo "Installing Python dependencies (groq)..."
pip3 install groq --break-system-packages 2>/dev/null || pip3 install groq
mkdir -p app
echo "Setup complete. Launching application..."
python3 main.py
