#!/bin/sh

pyinstaller \
    --hidden-import etesync_dav.radicale \
    --additional-hooks-dir ./hooks \
    --onefile \
    --windowed \
    ../scripts/etesync-dav
