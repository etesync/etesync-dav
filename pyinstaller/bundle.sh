#!/bin/sh

pyinstaller \
    --hidden-import radicale_storage_etesync \
    --hidden-import radicale_storage_etesync.rights \
    --onefile \
    ../scripts/etesync-dav
