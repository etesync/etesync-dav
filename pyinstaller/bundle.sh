#!/bin/sh

pyinstaller \
    --hidden-import etesync_dav.radicale \
    --additional-hooks-dir ./hooks \
    --onefile \
    ../scripts/etesync-dav
