#!/usr/bin/env bash
set -euo pipefail

app_id="app.mirror.Mirror"
bin_path="${XDG_BIN_HOME:-$HOME/.local/bin}/mirror"
app_file="${XDG_DATA_HOME:-$HOME/.local/share}/applications/${app_id}.desktop"

rm -f "$bin_path" "$app_file"
find "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" -name "${app_id}.png" -delete 2>/dev/null || true
gtk-update-icon-cache -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" >/dev/null 2>&1 || true
update-desktop-database "${XDG_DATA_HOME:-$HOME/.local/share}/applications" >/dev/null 2>&1 || true
echo "Mirror was removed from this account. The git clone is unchanged."
