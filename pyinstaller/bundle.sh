#!/bin/sh

# Icon is used on Mac and ignored on Linux
pyinstaller \
    --hidden-import etesync_dav.radicale \
    --additional-hooks-dir ./hooks \
    --onefile \
    --windowed \
    --icon ./ic_launcher.icns \
    ../scripts/etesync-dav
