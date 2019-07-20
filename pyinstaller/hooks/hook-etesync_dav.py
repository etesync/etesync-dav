from PyInstaller.utils.hooks import copy_metadata, collect_data_files

datas = copy_metadata('etesync_dav')
datas += collect_data_files('etesync_dav')
