pyinstaller ^
    --hidden-import etesync_dav.radicale ^
    --hidden-import radicale.auth.htpasswd ^
    --additional-hooks-dir .\hooks ^
    --onefile ^
    --windowed ^
    --icon .\ic_launcher.ico ^
    ..\scripts\etesync-dav
