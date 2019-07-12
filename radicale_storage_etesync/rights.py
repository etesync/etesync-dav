from radicale.rights import BaseRights

from .etesync_cache import EteSyncCache

import etesync as api

CONFIG_SECTION = "storage"


class Rights(BaseRights):
    def __init__(self, configuration, logger):
        super().__init__(configuration, logger)
        self._etesync_cache = EteSyncCache(
            creds_path=configuration.get(CONFIG_SECTION, "credentials_filename"),
            db_path=configuration.get(CONFIG_SECTION, "database_filename"),
            remote_url=configuration.get(CONFIG_SECTION, "remote_url"),
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
