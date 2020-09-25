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

from radicale import pathutils, rights

from .etesync_cache import etesync_for_user

import etesync as api


class Rights(rights.BaseRights):
    def authorization(self, user, path):
        if not user:
            return ""

        sane_path = pathutils.strip_path(path)
        if not sane_path:
            return "R"

        attributes = sane_path.split('/')
        if user != attributes[0]:
            return ""

        if "/" not in sane_path:
            return "RW"

        if sane_path.count("/") == 1:
            journal_uid = attributes[1]

            with etesync_for_user(user) as (etesync, _):
                try:
                    journal = etesync.get(journal_uid)
                except api.exceptions.DoesNotExist:
                    return ''

            return 'rw' if not journal.read_only else 'r'

        return ""
