#!/bin/sh
set -eu

DEFAULT_DIR="/etc/pwnagotchi/custom-plugins"
DEST="${PWN_CUSTOM_PLUGINS:-$DEFAULT_DIR}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STAMP=$(date +%Y%m%d-%H%M%S)

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root (for example: sudo ./install.sh)." >&2
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/doctor.py" ] || [ ! -d "$SCRIPT_DIR/doctor_packs" ]; then
  echo "This installer must be run from an assembled PwnDoctor release package." >&2
  exit 1
fi

mkdir -p "$DEST" /etc/pwnagotchi/doctor.d /var/lib/pwnagotchi/doctor

if [ -f "$DEST/doctor.py" ]; then
  cp -a "$DEST/doctor.py" "$DEST/doctor.py.bak-$STAMP"
  echo "Backed up existing doctor.py -> doctor.py.bak-$STAMP"
fi
if [ -d "$DEST/doctor_packs" ]; then
  cp -a "$DEST/doctor_packs" "$DEST/doctor_packs.bak-$STAMP"
  echo "Backed up existing doctor_packs -> doctor_packs.bak-$STAMP"
fi

install -m 0644 "$SCRIPT_DIR/doctor.py" "$DEST/doctor.py"
rm -rf "$DEST/doctor_packs"
cp -a "$SCRIPT_DIR/doctor_packs" "$DEST/doctor_packs"

echo
echo "PwnDoctor files installed to: $DEST"
echo
echo "This installer DOES NOT edit /etc/pwnagotchi/config.toml."
echo "Review: $SCRIPT_DIR/examples/doctor.config.toml"
echo "Then restart when ready: sudo systemctl restart pwnagotchi"
echo
echo "Recommended first run:"
echo '  main.plugins.doctor.autofix = "observe"'
echo '  main.plugins.doctor.dry_run = true'
