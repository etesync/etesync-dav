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

import radicale
from packaging.version import Version
from radicale import web

from etesync_dav.mac_helpers import has_ssl


class Web(web.BaseWeb):
    def _call(self, environ, base_prefix, path, user):
        from etesync_dav.webui import app

        ret_response = []

        def start_response(status, headers):
            ret_response.append(int(status.split()[0]))
            ret_response.append(dict(headers))

        if has_ssl():
            environ["wsgi.url_scheme"] = "https"
        body = list(app(environ, start_response))[0]
        ret_response.append(body)
        if Version(radicale.VERSION) >= Version("3.5.10"):
            ret_response.append(None)  # xml_request field
        return tuple(ret_response)

    def get(self, environ, base_prefix, path, user, *args, **kwargs):
        return self._call(environ, base_prefix, path, user)

    def post(self, environ, base_prefix, path, user, *args, **kwargs):
        return self._call(environ, base_prefix, path, user)
