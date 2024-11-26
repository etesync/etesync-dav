from PyInstaller.utils.hooks import collect_data_files

module_collection_mode = "py+pyz"
hiddenimports = ["orderedmultidict.__version__"]
datas = collect_data_files("orderedmultidict")
