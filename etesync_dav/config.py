from appdirs import user_config_dir
import os

CONFIG_DIR = user_config_dir("etesync-dav", "etesync")
HTPASSWD_FILE = os.path.join(CONFIG_DIR, 'htpaswd')
CREDS_FILE = os.path.join(CONFIG_DIR, 'etesync_creds')
RADICALE_CONFIG_FILE = os.path.join(CONFIG_DIR, 'radicale.conf')
ETESYNC_URL = os.environ.get('ETESYNC_URL', 'https://api.etesync.com/')
DATABASE_FILE = os.path.join(CONFIG_DIR, 'etesync_data.db')

RADICALE_CONFIG = """
[server]
hosts = localhost:37358

[storage]
type = radicale_storage_etesync

[auth]
type = htpasswd
htpasswd_filename = {}
htpasswd_encryption = plain

[etesync_storage]
database_filename = {}
remote_url = {}
credentials_filename = {}
""".format(HTPASSWD_FILE,
           DATABASE_FILE,
           ETESYNC_URL,
           CREDS_FILE)
