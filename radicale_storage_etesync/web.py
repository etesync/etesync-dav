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
