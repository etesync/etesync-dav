#!/bin/sh

set -e

ICON=ic_launcher.icns
if [ "$TRAVIS_OS_NAME" = "windows" ]; then
    ICON=ic_launcher.ico
fi

# Icon is used on Mac and ignored on Linux
pyinstaller \
    --hidden-import etesync_dav.radicale \
    --hidden-import radicale.auth.htpasswd \
    --additional-hooks-dir ./hooks \
    --onefile \
    --windowed \
    --icon $ICON \
    ../scripts/etesync-dav

# Travis stuff
mkdir deploy
if [ "$TRAVIS_OS_NAME" = "linux" ]; then
    mv dist/etesync-dav deploy/linux-etesync-dav
fi
if [ "$TRAVIS_OS_NAME" = "osx" ]; then
    cd dist
    zip -r mac-etesync-dav.zip *
    mv mac-etesync-dav.zip ../deploy/
    cd ../
fi
if [ "$TRAVIS_OS_NAME" = "windows" ]; then
    mv dist/etesync-dav.exe deploy/
fi
