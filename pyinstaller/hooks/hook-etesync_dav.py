from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_submodules

datas = copy_metadata('etesync_dav')
datas += collect_data_files('etesync_dav')

hiddenimports = collect_submodules('pkg_resources')
