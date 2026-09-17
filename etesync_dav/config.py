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

import os
from urllib.parse import urlsplit

from appdirs import user_config_dir, user_data_dir

LISTEN_ADDRESS = os.environ.get("ETESYNC_LISTEN_ADDRESS", "localhost")
LISTEN_PORT = os.environ.get("ETESYNC_LISTEN_PORT", "37358")

DEFAULT_HOSTS = "{}:{}".format(LISTEN_ADDRESS, LISTEN_PORT)

SERVER_HOSTS = os.environ.get("ETESYNC_SERVER_HOSTS", DEFAULT_HOSTS)
LEGACY_CONFIG_DIR = os.environ.get("ETESYNC_CONFIG_DIR", user_config_dir("etesync-dav", "etesync"))
DATA_DIR = os.environ.get("ETESYNC_DATA_DIR", user_data_dir("etesync-dav", "etesync"))

ETESYNC_URL = os.environ.get("ETESYNC_URL", "https://api.etebase.com/partner/etesync/")
LEGACY_ETESYNC_URL = os.environ.get("ETESYNC_URL", "https://api.etesync.com/")
DATABASE_FILE = os.environ.get("ETESYNC_DATABASE_FILE", os.path.join(DATA_DIR, "etesync_data.db"))
ETEBASE_DATABASE_FILE = os.environ.get("ETEBASE_DATABASE_FILE", os.path.join(DATA_DIR, "etebase_data.db"))

HTPASSWD_FILE = os.path.join(DATA_DIR, "htpaswd")
CREDS_FILE = os.path.join(DATA_DIR, "etesync_creds")

SSL_KEY_FILE = os.path.join(DATA_DIR, "etesync.key")
SSL_CERT_FILE = os.path.join(DATA_DIR, "etesync.crt")
LOG_FILE = os.path.join(DATA_DIR, "etesync-dav.log")


def local_server_url(scheme):
    """Return a browser-friendly URL for the first configured listener."""
    listener = SERVER_HOSTS.split(",", 1)[0].strip()
    try:
        parsed = urlsplit("//{}".format(listener))
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        host = None
        port = None

    if not host:
        host = LISTEN_ADDRESS
    if not port:
        port = LISTEN_PORT

    if host in {"0.0.0.0", "::", "[::]"}:
        host = "localhost"
    elif ":" in host:
        host = "[{}]".format(host)

    return "{}://{}:{}".format(scheme, host, port)
