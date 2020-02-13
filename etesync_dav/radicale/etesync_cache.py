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
import hashlib
import threading
import collections
import os
from contextlib import contextmanager

from urllib.parse import quote

import etesync as api
from etesync_dav import config

from .href_mapper import HrefMapper


class EteSync(api.EteSync):
    def _init_db_tables(self, database, additional_tables=[]):
        super()._init_db_tables(database, additional_tables + [HrefMapper])


class NamedReverseSemaphore:
    _data_lock = threading.RLock()
    _named_cond = collections.OrderedDict()

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def _unref_name_self(self):
        cls = NamedReverseSemaphore
        with cls._data_lock:
            cls._named_cond[self.name][1] -= 1
            if cls._named_cond[self.name][1] == 0:
                del cls._named_cond[self.name]

                return True
        return False

    def acquire(self, timeout=None):
        cls = NamedReverseSemaphore
        cond = None
        with cls._data_lock:
            if not cls._named_cond:
                cls._named_cond[self.name] = [None, 1]
                return True
            elif next(iter(cls._named_cond)) == self.name:
                cls._named_cond[self.name][1] += 1
                return True
            else:
                if self.name not in cls._named_cond:
                    cond = threading.Condition()
                    cls._named_cond[self.name] = [cond, 1]
                else:
                    cond = cls._named_cond[self.name][0]
                    cls._named_cond[self.name][1] += 1
                cond.acquire()
        if cond is not None:
            ret = cond.wait(timeout=timeout)

            cond.release()
            if not ret:
                self._unref_name_self()
            return ret
        else:
            raise RuntimeError('Condition is None, should never happen!')

    def release(self):
        cls = NamedReverseSemaphore
        cond = None
        with cls._data_lock:
            owner = next(iter(cls._named_cond))
            if owner == self.name:
                if self._unref_name_self():
                    if cls._named_cond:
                        cond, refcount = next(iter(cls._named_cond.values()))
                        cond.acquire()
            else:
                raise RuntimeError('NamedReverseSemaphore: did not own lock at exit. Owner: ' + str(owner))
        if cond is not None:
            cond.notify_all()
            cond.release()

class EteSyncCache:
    def __init__(self, creds_path, db_path, remote_url=None):
        self._etesync_cache = {}
        self.creds = None
        self.creds_path = os.path.expanduser(creds_path)
        self.db_path = os.path.expanduser(db_path)
        self.remote_url = os.environ.get('ETESYNC_URL', remote_url)

    def etesync_for_user(self, user):
        if self.creds:
            # Always attempt a reload
            self.creds.load()

            # Used the cached etesync for the user unless the cipher_key or auth_token have changed.
            if user in self._etesync_cache:
                etesync = self._etesync_cache[user]
                if (etesync.auth_token, etesync.cipher_key) == self.creds.get(user):
                    etesync.reinit()
                    return etesync, False
                else:
                    del self._etesync_cache[user]
        else:
            self.creds = Credentials(self.creds_path)

        auth_token, cipher_key = self.creds.get(user)

        # Create a unique filename for user and cipher_key combos. So we don't use old caches that are no longer valid.
        unique_name_sha = hashlib.sha256(cipher_key)
        db_name_unique = '{}-{}'.format(quote(user, safe=''), unique_name_sha.hexdigest())

        db_path = self.db_path.format(db_name_unique)

        if auth_token is None:
            raise Exception('Very bad! User "{}" not found in credentials file.'.format(user))

        etesync = EteSync(user, auth_token, remote=self.remote_url, db_path=db_path)
        etesync.cipher_key = cipher_key

        self._etesync_cache[user] = etesync

        return etesync, True


_etesync_cache = EteSyncCache(
    creds_path=config.CREDS_FILE,
    db_path=config.DATABASE_FILE,
    remote_url=config.ETESYNC_URL,
)


@contextmanager
def etesync_for_user(user):
    with NamedReverseSemaphore(user):
        yield _etesync_cache.etesync_for_user(user)
