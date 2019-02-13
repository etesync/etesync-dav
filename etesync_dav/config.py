from appdirs import user_config_dir
import os

LISTEN_ADDRESS = os.environ.get('ETESYNC_LISTEN_ADDRESS', 'localhost')
LISTEN_PORT = os.environ.get('ETESYNC_LISTEN_PORT', '37358')
CONFIG_DIR = os.environ.get('ETESYNC_CONFIG_DIR', user_config_dir("etesync-dav", "etesync"))
HTPASSWD_FILE = os.path.join(CONFIG_DIR, 'htpaswd')
CREDS_FILE = os.path.join(CONFIG_DIR, 'etesync_creds')
RADICALE_CONFIG_FILE = os.path.join(CONFIG_DIR, 'radicale.conf')
ETESYNC_URL = os.environ.get('ETESYNC_URL', 'https://api.etesync.com/')
DATABASE_FILE = os.path.join(CONFIG_DIR, 'etesync_data.db')

RADICALE_CONFIG = """
[server]
hosts = {}:{}

[auth]
type = htpasswd
htpasswd_filename = {}
htpasswd_encryption = plain

[storage]
type = radicale_storage_etesync
database_filename = {}
remote_url = {}
credentials_filename = {}

[rights]
type = radicale_storage_etesync.rights
""".format(LISTEN_ADDRESS,
           LISTEN_PORT,
           HTPASSWD_FILE,
           DATABASE_FILE,
           ETESYNC_URL,
           CREDS_FILE)
