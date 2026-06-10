#!/bin/bash
DESKTOP_FILE="$HOME/.local/share/applications/ice-tracker.desktop"
mkdir -p "$HOME/.local/share/applications"
cat << DESK_EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Name=ICE Detention Tracker
Comment=Logistics Command Center
Exec=$APP_DIR/run.sh
Icon=system-run
Terminal=false
Type=Application
Categories=Network;Utility;
DESK_EOF
update-desktop-database "$HOME/.local/share/applications"
