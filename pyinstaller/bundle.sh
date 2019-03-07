#!/bin/sh

pyinstaller \
    --hidden-import radicale_storage_etesync \
    --hidden-import radicale_storage_etesync.rights \
    --additional-hooks-dir ./hooks \
    --onefile \
    ../scripts/etesync-dav
