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

import os
import random
import string
import time
import hashlib

import etesync as api
import etebase as Etebase
from .radicale.creds import Credentials
from .radicale.etesync_cache import etesync_for_user
from . import local_cache
from etesync_dav.config import CREDS_FILE, HTPASSWD_FILE, LEGACY_ETESYNC_URL, ETESYNC_URL, DATA_DIR, LEGACY_CONFIG_DIR


class Htpasswd:
    def __init__(self, filename):
        self.filename = filename
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                self.content = dict(map(lambda x: x.strip(), line.split(':', 1)) for line in f)
        else:
            self.content = {}

    def save(self):
        with open(self.filename, "w") as f:
            for name, password in self.content.items():
                print("{}:{}".format(name, password), file=f)

    def get(self, username):
        return self.content.get(username, None)

    def set(self, username, password):
        self.content[username] = password

    def delete(self, username):
        self.content.pop(username, None)

    def list(self):
        for item in self.content.keys():
            yield item


class Manager:
    def __init__(self,
                 config_dir=DATA_DIR, htpasswd_file=HTPASSWD_FILE, creds_file=CREDS_FILE):

        if not os.path.exists(config_dir):
            # If the old dir still exists and the new one doesn't, mv the location
            if os.path.exists(LEGACY_CONFIG_DIR):
                import shutil
                shutil.move(LEGACY_CONFIG_DIR, DATA_DIR)
            else:
                os.makedirs(config_dir, mode=0o700)

        self.htpasswd = Htpasswd(htpasswd_file)
        self.creds = Credentials(creds_file)

        if not os.path.exists(htpasswd_file):
            # Create a missing htpasswd file if missing
            self.htpasswd.save()

    def _generate_pasword(self):
        return ''.join(
                [random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for i in range(16)])

    def validate_username(self, username):
        if username is None:
            raise RuntimeError("Username is required")
        if ':' in username:
            raise RuntimeError("Username can't include a colon.")
        return self.htpasswd.get(username) is not None

    def refresh_token(self, username, login_password):
        server_url = self.creds.get_server_url(username)
        stored_session = self.creds.get_etebase(username)
        if stored_session is not None:
            etebase = local_cache.Etebase(username, stored_session, server_url).etebase
            etebase.fetch_token()
            self.creds.set_etebase(username, etebase.save(None), server_url)
        else:
            _, cipher_key = self.creds.get(username)
            if cipher_key is None:
                raise RuntimeError("User not found in etesync-dav")
            auth_token = api.Authenticator(server_url).get_auth_token(username, login_password)
            self.creds.set(username, auth_token, cipher_key, server_url)

        self.creds.save()

    def add(self, username, login_password, encryption_password, remote_url=LEGACY_ETESYNC_URL):
        exists = self.validate_username(username)
        if exists:
            raise RuntimeError("User already exists. Delete first if you'd like to override settings.")

        print("Fetching auth token")
        auth_token = api.Authenticator(remote_url).get_auth_token(username, login_password)

        print("Deriving password")
        etesync = api.EteSync(username, auth_token, remote=remote_url, db_path=':memory:')
        cipher_key = etesync.derive_key(encryption_password)

        print("Saving config")
        generated_password = self._generate_pasword()
        self.htpasswd.set(username, generated_password)
        self.creds.set(username, auth_token, cipher_key, remote_url)
        self.htpasswd.save()
        self.creds.save()

        print("Initializing account")
        try:
            with etesync_for_user(username) as (etesync, _):
                etesync.get_or_create_user_info(force_fetch=True)
                etesync.sync_journal_list()
                if not list(etesync.list()):
                    collection_info = {"displayName": "My Calendar", "description": ""}
                    collection_name = hashlib.sha256(str(time.time()).encode()).hexdigest()
                    inst = api.Calendar.create(etesync, collection_name, collection_info)
                    inst.save()

                    collection_info = {"displayName": "My Tasks", "description": ""}
                    collection_name = hashlib.sha256(str(time.time()).encode()).hexdigest()
                    inst = api.TaskList.create(etesync, collection_name, collection_info)
                    inst.save()

                    collection_info = {"displayName": "My Contacts", "description": ""}
                    collection_name = hashlib.sha256(str(time.time()).encode()).hexdigest()
                    inst = api.AddressBook.create(etesync, collection_name, collection_info)
                    inst.save()

                    etesync.sync_journal_list()
        except Exception as e:
            # Remove the username on error
            self.htpasswd.delete(username)
            self.creds.delete(username)
            self.htpasswd.save()
            self.creds.save()
            raise e

        return self.get(username)

    def add_etebase(self, username, password, remote_url=ETESYNC_URL):
        exists = self.validate_username(username)
        if exists:
            raise RuntimeError("User already exists. Delete first if you'd like to override settings.")

        print("Logging in")
        client = Etebase.Client("etesync-dav", remote_url)
        etebase = Etebase.Account.login(client, username, password)

        print("Saving config")
        generated_password = self._generate_pasword()
        self.htpasswd.set(username, generated_password)
        self.creds.set_etebase(username, etebase.save(None), remote_url)
        self.htpasswd.save()
        self.creds.save()

        print("Initializing account")
        try:
            col_mgr = etebase.get_collection_manager()
            fetch_options = Etebase.FetchOptions().limit(1)
            collections = col_mgr.list(local_cache.COL_TYPES, fetch_options)

            # This means its a new account, so create default collections
            if len(list(collections.data)) == 0:
                wanted = [
                    ["etebase.vcard", "My Contacts"],
                    ["etebase.vevent", "My Calendar"],
                    ["etebase.vtodo", "My Tasks"],
                ]
                try:
                    for [col_type, name] in wanted:
                        meta = {"name": name, "mtime": local_cache.get_millis()}
                        col = col_mgr.create(col_type, meta, b"")
                        col_mgr.upload(col)
                except Exception as e:
                    print("Failed creating default collections (skipping). Reason:", e)
                    pass
        except Exception as e:
            # Remove the username on error
            self.htpasswd.delete(username)
            self.creds.delete(username)
            self.htpasswd.save()
            self.creds.save()
            raise e

        return self.get(username)

    def delete(self, username):
        exists = self.validate_username(username)
        if not exists:
            raise RuntimeError("User not found")

        try:
            with etesync_for_user(username) as (etesync, _):
                if hasattr(etesync, 'clear_user'):
                    etesync.clear_user()
                else:
                    # Legacy etesync, do manually:
                    user = etesync.user
                    for col in user.journals:
                        for item in col.entries:
                            item.delete_instance()
                        col.delete_instance()
                    user.user_info.delete_instance()
                    user.delete()
                    user = None
        except Exception as e:
            print("Failed removing user cache", e)

        self.htpasswd.delete(username)
        self.creds.delete(username)
        self.htpasswd.save()
        self.creds.save()

    def get(self, username):
        exists = self.validate_username(username)
        if not exists:
            raise RuntimeError("User not found")

        return self.htpasswd.get(username)

    def list(self):
        for user in self.htpasswd.list():
            yield user
