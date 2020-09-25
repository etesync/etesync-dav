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

import base64
import json
import os

from etesync_dav.config import LEGACY_ETESYNC_URL


class Credentials:
    def __init__(self, filename):
        self.filename = filename
        self.last_mtime = 0
        self.content = {'users': {}}
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            mtime = os.path.getmtime(self.filename)
            if mtime != self.last_mtime:
                with open(self.filename, "r") as f:
                    self.content = json.load(f)
            self.last_mtime = mtime

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.content, f)

    def get_server_url(self, username):
        users = self.content['users']
        if username not in users:
            return None

        user = users[username]
        return user.get('serverUrl', LEGACY_ETESYNC_URL)

    def get(self, username):
        users = self.content['users']
        if username not in users:
            return None, None

        user = users[username]
        return user['authToken'], base64.b64decode(user['cipherKey'])

    def set(self, username, auth_token, cipher_key, server_url):
        users = self.content['users']
        user = {
                'authToken': auth_token,
                'cipherKey': base64.b64encode(cipher_key).decode(),
                'serverUrl': server_url
            }
        users[username] = user

    def get_etebase(self, username):
        users = self.content['users']
        if username not in users:
            return None

        user = users[username]
        return user.get('storedSession', None)

    def set_etebase(self, username, stored_session, server_url):
        users = self.content['users']
        user = {
                'storedSession': stored_session,
                'serverUrl': server_url
            }
        users[username] = user

    def delete(self, username):
        users = self.content['users']
        users.pop(username, None)
