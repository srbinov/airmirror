#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
app_id="app.mirror.Mirror"
bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
app_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icon_dir="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
bin_path="$bin_dir/mirror"

mkdir -p "$bin_dir" "$app_dir" "$icon_dir"

cat > "$bin_path" <<EOF
#!/usr/bin/env python3
import sys
sys.path.insert(0, ${root@Q})
from mirror.identity import apply
apply()
from mirror.app import main
raise SystemExit(main())
EOF
chmod +x "$bin_path"

cp -a "$root/data/icons/hicolor/." "$icon_dir/"
gtk-update-icon-cache -f "$icon_dir" >/dev/null 2>&1 || true

cat > "$app_dir/${app_id}.desktop" <<EOF
[Desktop Entry]
Name=Mirror
Comment=AirPlay receiver for this computer
Exec=${bin_path}
Path=${root}
Icon=${app_id}
Terminal=false
Type=Application
Categories=AudioVideo;Network;
StartupNotify=true
StartupWMClass=${app_id}
EOF

update-desktop-database "$app_dir" >/dev/null 2>&1 || true

echo "Mirror is installed."
echo "  launcher: search for “Mirror” in the app grid"
echo "  command:  $bin_path"
echo "Keep this clone at $root — the launcher runs from here."
