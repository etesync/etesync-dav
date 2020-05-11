pyinstaller ^
    --hidden-import etesync_dav.radicale ^
    --additional-hooks-dir .\hooks ^
    --onefile ^
    --windowed ^
    --icon .\ic_launcher.ico ^
    ..\scripts\etesync-dav
