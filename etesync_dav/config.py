# Copyright © 2017 Tom Hacohen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from appdirs import user_config_dir, user_data_dir
import os

LISTEN_ADDRESS = os.environ.get('ETESYNC_LISTEN_ADDRESS', 'localhost')
LISTEN_PORT = os.environ.get('ETESYNC_LISTEN_PORT', '37358')

DEFAULT_HOSTS = '{}:{}'.format(LISTEN_ADDRESS, LISTEN_PORT)

SERVER_HOSTS = os.environ.get('ETESYNC_SERVER_HOSTS', DEFAULT_HOSTS)
LEGACY_CONFIG_DIR = os.environ.get('ETESYNC_CONFIG_DIR', user_config_dir("etesync-dav", "etesync"))
DATA_DIR = os.environ.get('ETESYNC_DATA_DIR', user_data_dir("etesync-dav", "etesync"))

ETESYNC_URL = os.environ.get('ETESYNC_URL', 'https://api.etebase.com/partner/etesync/')
LEGACY_ETESYNC_URL = os.environ.get('ETESYNC_URL', 'https://api.etesync.com/')
DATABASE_FILE = os.environ.get('ETESYNC_DATABASE_FILE', os.path.join(DATA_DIR, 'etesync_data.db'))
ETEBASE_DATABASE_FILE = os.environ.get('ETEBASE_DATABASE_FILE', os.path.join(DATA_DIR, 'etebase_data.db'))

HTPASSWD_FILE = os.path.join(DATA_DIR, 'htpaswd')
CREDS_FILE = os.path.join(DATA_DIR, 'etesync_creds')

SSL_KEY_FILE = os.path.join(DATA_DIR, 'etesync.key')
SSL_CERT_FILE = os.path.join(DATA_DIR, 'etesync.crt')
