import os
import random
import string
import time
import hashlib

import etesync as api
from .radicale.creds import Credentials
from .radicale.etesync_cache import etesync_for_user
from etesync_dav.config import CREDS_FILE, HTPASSWD_FILE, ETESYNC_URL, CONFIG_DIR


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
                 config_dir=CONFIG_DIR, htpasswd_file=HTPASSWD_FILE, creds_file=CREDS_FILE, remote_url=ETESYNC_URL):

        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        self.htpasswd = Htpasswd(htpasswd_file)
        self.creds = Credentials(creds_file)

        self.remote_url = remote_url

    def _generate_pasword(self):
        return ''.join(
                [random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for i in range(16)])

    def validate_username(self, username):
        if username is None:
            raise RuntimeError("Username is required")
        if ':' in username:
            raise RuntimeError("Username can't include a colon.")
        return self.htpasswd.get(username) is not None

    def add(self, username, login_password, encryption_password):
        exists = self.validate_username(username)
        if exists:
            raise RuntimeError("User already exists. Delete first if you'd like to override settings.")

        print("Fetching auth token")
        auth_token = api.Authenticator(self.remote_url).get_auth_token(username, login_password)

        print("Deriving password")
        etesync = api.EteSync(username, auth_token, remote=self.remote_url, db_path=':memory:')
        cipher_key = etesync.derive_key(encryption_password)

        print("Saving config")
        generated_password = self._generate_pasword()
        self.htpasswd.set(username, generated_password)
        self.creds.set(username, auth_token, cipher_key)
        self.htpasswd.save()
        self.creds.save()

        print("Initializing account")
        try:
            with etesync_for_user(username) as (etesync, _):
                etesync.get_or_create_user_info(force_fetch=True)
                etesync.sync_journal_list()
                if not list(etesync.list()):
                    collection_info = {"displayName": "Default", "description": ""}

                    collection_name = hashlib.sha256(str(time.time()).encode()).hexdigest()
                    inst = api.Calendar.create(etesync, collection_name, collection_info)
                    inst.save()

                    collection_name = hashlib.sha256(str(time.time()).encode()).hexdigest()
                    inst = api.TaskList.create(etesync, collection_name, collection_info)
                    inst.save()

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

    def delete(self, username):
        exists = self.validate_username(username)
        if not exists:
            raise RuntimeError("User not found")

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
