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
