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

from .creds import Credentials
import threading
import os
from contextlib import contextmanager

import etesync as api
from etesync_dav import config

from .href_mapper import HrefMapper

from ..local_cache import Etebase


class EteSync(api.EteSync):
    def _init_db_tables(self, database, additional_tables=[]):
        super()._init_db_tables(database, additional_tables + [HrefMapper])


class EteSyncCache:
    def __init__(self, creds_path, db_path):
        self._etesync_cache = {}
        self.creds = None
        self.creds_path = os.path.expanduser(creds_path)
        self.db_path = os.path.expanduser(db_path)

    def etesync_for_user(self, user):
        if self.creds:
            # Always attempt a reload
            self.creds.load()

            # Used the cached etesync for the user unless the cipher_key or auth_token have changed.
            if user in self._etesync_cache:
                etesync = self._etesync_cache[user]
                if isinstance(etesync, Etebase) and (etesync.stored_session == self.creds.get_etebase(user)):
                    return etesync, False
                elif isinstance(etesync, EteSync) and \
                        ((etesync.auth_token, etesync.cipher_key) == self.creds.get(user)):
                    return etesync, False
                else:
                    del self._etesync_cache[user]
        else:
            self.creds = Credentials(self.creds_path)

        remote_url = self.creds.get_server_url(user)
        stored_session = self.creds.get_etebase(user)
        if stored_session is not None:
            etesync = Etebase(user, stored_session, remote_url)
        else:
            auth_token, cipher_key = self.creds.get(user)

            db_name_unique = 'generic'

            db_path = self.db_path.format(db_name_unique)

            if auth_token is None:
                raise Exception('Very bad! User "{}" not found in credentials file.'.format(user))

            etesync = EteSync(user, auth_token, remote=remote_url, db_path=db_path)
            etesync.cipher_key = cipher_key

        self._etesync_cache[user] = etesync

        return etesync, True


_etesync_cache = EteSyncCache(
    creds_path=config.CREDS_FILE,
    db_path=config.DATABASE_FILE,
)


_get_etesync_lock = threading.RLock()


@contextmanager
def etesync_for_user(user):
    with _get_etesync_lock:
        ret = _etesync_cache.etesync_for_user(user)

    yield ret
