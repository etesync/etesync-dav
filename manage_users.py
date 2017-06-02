#!/usr/bin/env python

import argparse
from configparser import RawConfigParser as ConfigParser
import random
import string

import etesync as api
from radicale_storage_etesync import creds, CONFIG_SECTION


HTPASSWD_FILE = './htpaswd'
CREDS_FILE = './etesync_creds'
RADICALE_CONFIG_FILE = './radicale.conf'
ETESYNC_PORT = 37358


class Htpasswd:
    def __init__(self, filename):
        self.filename = filename
        self.load()

    def load(self):
        with open(self.filename, "r") as f:
            self.content = dict(map(lambda x: x.strip(), line.split(':', 1)) for line in f)

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


def print_credentials(htpasswd, username):
    print("Please configure your email client to use the following credentials:\n")
    print("Server: http://localhost:{}".format(ETESYNC_PORT))
    print("User: {}\nPassword: {}".format(args.username, htpasswd.get(args.username)))


parser = argparse.ArgumentParser()
parser.add_argument("command",
                    choices=('add', 'del', 'get'),
                    help="Either add to add a user, del to remove a user, or get to show login creds.")
parser.add_argument("username",
                    help="The username used with EteSync")
parser.add_argument("--login-password",
                    help="The password to login to the EteSync server.")
parser.add_argument("--encryption-password",
                    help="The encryption password")
args = parser.parse_args()


if ':' in args.username:
    raise RuntimeError("Username can't include a colon.")

htpasswd = Htpasswd(HTPASSWD_FILE)
creds = creds.Credentials(CREDS_FILE)
radicale_config = ConfigParser()
radicale_config.read(RADICALE_CONFIG_FILE)

remote_url = radicale_config.get(CONFIG_SECTION, "remote_url")
db_path = radicale_config.get(CONFIG_SECTION, "database_filename")
creds_path = radicale_config.get(CONFIG_SECTION, "credentials_filename")
exists = htpasswd.get(args.username) is not None

if args.command == 'add':
    if exists:
        raise RuntimeError("User already exists. Delete first if you'd like to override settings.")

    print("Fetching auth token")
    auth_token = api.Authenticator(remote_url).get_auth_token(args.username, args.login_password)

    print("Deriving password")
    etesync = api.EteSync(args.username, auth_token, remote=remote_url)
    cipher_key = etesync.derive_key(args.encryption_password)

    print("Saving config")
    generated_password = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=16))
    htpasswd.set(args.username, generated_password)
    creds.set(args.username, auth_token, cipher_key)
    htpasswd.save()
    creds.save()

    print_credentials(htpasswd, args.username)

elif args.command == 'del':
    if not exists:
        raise RuntimeError("User not found")

    print("Deleting user")
    htpasswd.delete(args.username)
    creds.delete(args.username)
    htpasswd.save()
    creds.save()

elif args.command == 'get':
    if not exists:
        raise RuntimeError("User not found")

    print_credentials(htpasswd, args.username)
