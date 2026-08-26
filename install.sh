#!/bin/sh
# Symlink into place and start the background switcher. Re-runnable.
set -e
cd "$(dirname "$0")"
mkdir -p ~/.local/bin ~/.config/systemd/user ~/.local/share/applications \
    ~/.local/share/icons/hicolor/scalable/apps ~/.local/share/icons/hicolor/scalable/status
# A per-user hicolor directory needs the theme index before GTK will scan or
# cache it. Reuse the system index without replacing a user-owned one.
if [ ! -e ~/.local/share/icons/hicolor/index.theme ] && \
        [ -e /usr/share/icons/hicolor/index.theme ]; then
    ln -s /usr/share/icons/hicolor/index.theme ~/.local/share/icons/hicolor/index.theme
fi
ln -sf "$PWD/powerswitch" ~/.local/bin/powerswitch
ln -sf "$PWD/powerswitch.service" ~/.config/systemd/user/powerswitch.service
ln -sf "$PWD/powerswitch.desktop" ~/.local/share/applications/powerswitch.desktop
ln -sf "$PWD/icons/powerswitch.svg" ~/.local/share/icons/hicolor/scalable/apps/powerswitch.svg
ln -sf "$PWD/icons/powerswitch-symbolic.svg" ~/.local/share/icons/hicolor/scalable/status/powerswitch-symbolic.svg
update-desktop-database ~/.local/share/applications 2>/dev/null || true
gtk-update-icon-cache -f ~/.local/share/icons/hicolor 2>/dev/null || true

if systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable --now powerswitch.service
    echo "Installed. Run 'powerswitch' or open Power Switch from the app grid."
else
    echo "Files installed. No user systemd session here, so the background"
    echo "switcher was not started — run 'systemctl --user enable --now powerswitch'"
    echo "once you are logged into a desktop."
fi
