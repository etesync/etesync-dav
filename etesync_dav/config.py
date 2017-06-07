from appdirs import user_config_dir
import os

CONFIG_DIR = user_config_dir("etesync-dav", "etesync")
HTPASSWD_FILE = os.path.join(CONFIG_DIR, 'htpaswd')
CREDS_FILE = os.path.join(CONFIG_DIR, 'etesync_creds')
RADICALE_CONFIG_FILE = os.path.join(CONFIG_DIR, 'radicale.conf')

RADICALE_CONFIG = """
[server]
hosts = localhost:37358

[storage]
type = radicale_storage_etesync

[auth]
type = htpasswd
htpasswd_filename = ./htpaswd
htpasswd_encryption = plain

[etesync_storage]
database_filename = ./etesync_data.db
remote_url = https://api.etesync.com/
credentials_filename = ./etesync_creds
"""
