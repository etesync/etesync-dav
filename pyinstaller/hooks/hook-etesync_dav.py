from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = copy_metadata("etesync_dav")
datas += collect_data_files("etesync_dav")

hiddenimports = collect_submodules("pkg_resources")
