from radicale.rights import BaseRights

from .etesync_cache import EteSyncCache

import etesync as api

import etesync_dav.config as config


class Rights(BaseRights):
    def __init__(self, configuration, logger):
        super().__init__(configuration, logger)
        self._etesync_cache = EteSyncCache(
            creds_path=config.CREDS_FILE,
            db_path=config.DATABASE_FILE,
            remote_url=config.ETESYNC_URL,
        )

    def authorized(self, user, path, permission):
        if not bool(user):
            return False

        attributes = path.strip('/').split('/')

        if len(attributes) == 1:
            if attributes[0] == '':
                return permission == 'r'
            else:
                return attributes[0] == user

        if attributes[0] != user:
            return False

        if permission == 'r':
            return True

        journal_uid = attributes[1]

        with EteSyncCache.lock:
            etesync, _ = self._etesync_cache.etesync_for_user(user)
            try:
                journal = etesync.get(journal_uid)
            except api.exceptions.DoesNotExist:
                return False

        return not journal.read_only
