from appdirs import user_config_dir
import os

LISTEN_ADDRESS = os.environ.get('ETESYNC_LISTEN_ADDRESS', 'localhost')
LISTEN_PORT = os.environ.get('ETESYNC_LISTEN_PORT', '37358')
CONFIG_DIR = os.environ.get('ETESYNC_CONFIG_DIR', user_config_dir("etesync-dav", "etesync"))
ETESYNC_URL = os.environ.get('ETESYNC_URL', 'https://api.etesync.com/')
DATABASE_FILE = os.environ.get('ETESYNC_DATABASE_FILE', os.path.join(CONFIG_DIR, 'etesync_data.db'))

ETESYNC_MANAGEMENT_URL = os.environ.get('ETESYNC_MANAGEMENT_URL', 'http://localhost:37359')

HTPASSWD_FILE = os.path.join(CONFIG_DIR, 'htpaswd')
CREDS_FILE = os.path.join(CONFIG_DIR, 'etesync_creds')

SSL_KEY_FILE = os.path.join(CONFIG_DIR, 'etesync.key')
SSL_CERT_FILE = os.path.join(CONFIG_DIR, 'etesync.crt')
