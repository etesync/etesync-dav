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

import pkg_resources

from radicale import web

from etesync_dav.mac_helpers import has_ssl


class Web(web.BaseWeb):
    def __init__(self, configuration):
        super().__init__(configuration)
        self.folder = pkg_resources.resource_filename(__name__, "web")

    def _call(self, environ, base_prefix, path, user):
        from etesync_dav.webui import app
        ret_response = []

        def start_response(status, headers):
            ret_response.append(int(status.split()[0]))
            ret_response.append(dict(headers))

        if has_ssl():
            environ['wsgi.url_scheme'] = 'https'
        body = list(app(environ, start_response))[0]
        ret_response.append(body)
        return tuple(ret_response)

    def get(self, environ, base_prefix, path, user):
        return self._call(environ, base_prefix, path, user)

    def post(self, environ, base_prefix, path, user):
        return self._call(environ, base_prefix, path, user)
