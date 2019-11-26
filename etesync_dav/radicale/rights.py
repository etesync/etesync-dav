from radicale.rights import BaseRights

from .etesync_cache import EteSyncCache, etesync_for_user

import etesync as api


class Rights(BaseRights):
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

        with etesync_for_user(user) as (etesync, _):
            try:
                journal = etesync.get(journal_uid)
            except api.exceptions.DoesNotExist:
                return False

        return not journal.read_only
