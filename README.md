# Mirror

A Linux AirPlay receiver with a real window. Your iPhone or Mac sees this computer like an Apple TV: screen mirroring lands in the app, songs show cover art and track info, and audio plays through the system speakers.

The AirPlay engine is [UxPlay](https://github.com/FDH2/UxPlay). This app starts it, embeds the video, and provides the GTK interface.

## Requirements

- Linux with GNOME or another GTK4 desktop (tested on Ubuntu)
- Python 3.12+
- An iPhone, iPad, or Mac on the **same Wi-Fi** (or Ethernet) as this computer

## Install

### 1. Packages

```bash
sudo apt update
sudo apt install -y \
  git \
  uxplay \
  avahi-daemon \
  gstreamer1.0-gtk4 \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-libav \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-4.0 \
  gir1.2-adw-1 \
  gir1.2-gstreamer-1.0 \
  gir1.2-gst-plugins-base-1.0
sudo systemctl enable --now avahi-daemon
```

Fedora:

```bash
sudo dnf install uxplay avahi python3-gobject gtk4 libadwaita \
  gstreamer1-plugins-good gstreamer1-plugins-bad-free gstreamer1-plugin-gtk4
sudo systemctl enable --now avahi-daemon
```

### 2. Clone and install the launcher

```bash
git clone https://github.com/YOUR_USER/airmirror.git
cd airmirror
chmod +x bin/mirror scripts/install.sh scripts/uninstall.sh
./scripts/install.sh
```

That puts a `mirror` command in `~/.local/bin` and a **Mirror** entry in the app grid, with the phones icon on the dock. Keep the clone where you put it; the launcher runs from that directory.

If `~/.local/bin` is not on your `PATH`, either add it or always use the full path printed by the install script.

### 3. Open the app

Search the app grid for **Mirror**, or:

```bash
mirror
```

## Use it

1. Click **Start**.
2. On iPhone or Mac, open Control Center.
3. For the whole phone screen: **Screen Mirroring** → **Mirror**.
4. For music: play a song and AirPlay it to **Mirror**. Cover art, title, and artist show in the window; sound comes out of this computer.

Name, optional password (6+ characters), fullscreen-on-connect, and starting volume are under **Settings**. Stop and Start again after changing them.

## Uninstall

```bash
./scripts/uninstall.sh
```

Then remove the clone if you want. Packages such as `uxplay` stay installed until you remove them with apt/dnf.

## Troubleshooting

**The iPhone cannot see Mirror**  
Confirm both devices are on the same network, `avahi-daemon` is running (`systemctl status avahi-daemon`), and a firewall is not blocking mDNS (UDP 5353) or the AirPlay ports UxPlay opens.

**`kDNSServiceErr_NameConflict`**  
Another UxPlay/Mirror instance is already advertising that name. Quit extra Mirror windows, then Start once. The app now clears leftover `uxplay` processes on Start.

**Connected, but a blank waiting screen**  
Use Control Center → **Screen Mirroring** for video. Playing a song to Mirror as a speaker shows Now Playing, not the home screen. After `gstreamer1.0-gtk4` is installed, Stop and Start so video can embed in this window.

**Dock still shows a Python icon**  
Run `./scripts/install.sh` again, then launch from the app grid (not a random `python3` command).

## Development

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 -m mirror
```

## License

GPL-3.0. UxPlay is GPL-3.0.
