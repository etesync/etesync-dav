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

from http import client

import pkg_resources

from radicale import web
from etesync_dav.config import ETESYNC_MANAGEMENT_URL


class Web(web.BaseWeb):
    def __init__(self, configuration, logger):
        super().__init__(configuration, logger)
        self.folder = pkg_resources.resource_filename(__name__, "web")

    def get(self, environ, base_prefix, path, user):
        location = ETESYNC_MANAGEMENT_URL
        return (client.FOUND,
                {"Location": location, "Content-Type": "text/plain"},
                "Redirected to %s" % location)
