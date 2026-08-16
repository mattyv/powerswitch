#!/bin/sh
# Symlink into place and start the background switcher. Re-runnable.
set -e
cd "$(dirname "$0")"
mkdir -p ~/.local/bin ~/.config/systemd/user ~/.local/share/applications
ln -sf "$PWD/powerswitch" ~/.local/bin/powerswitch
ln -sf "$PWD/powerswitch.service" ~/.config/systemd/user/powerswitch.service
ln -sf "$PWD/powerswitch.desktop" ~/.local/share/applications/powerswitch.desktop
update-desktop-database ~/.local/share/applications 2>/dev/null || true

if systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable --now powerswitch.service
    echo "Installed. Run 'powerswitch' or open Power Switch from the app grid."
else
    echo "Files installed. No user systemd session here, so the background"
    echo "switcher was not started — run 'systemctl --user enable --now powerswitch'"
    echo "once you are logged into a desktop."
fi
