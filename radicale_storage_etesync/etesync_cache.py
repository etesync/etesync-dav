from .creds import Credentials
import hashlib
import threading
import os

from urllib.parse import quote

import etesync as api
from .href_mapper import HrefMapper


class EteSync(api.EteSync):
    def _init_db_tables(self, database, additional_tables=[]):
        super()._init_db_tables(database, additional_tables + [HrefMapper])


class EteSyncCache:
    lock = threading.RLock()

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
                    # FIXME: Reinit the etesync db - should use the official reinit function once released
                    etesync._set_db(etesync._database)
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
