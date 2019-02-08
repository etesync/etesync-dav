import base64
import json
import os


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

    def get(self, username):
        users = self.content['users']
        if username not in users:
            return None, None

        user = users[username]
        return user['authToken'], base64.b64decode(user['cipherKey'])

    def set(self, username, auth_token, cipher_key):
        users = self.content['users']
        user = {
                'authToken': auth_token,
                'cipherKey': base64.b64encode(cipher_key).decode(),
            }
        users[username] = user

    def delete(self, username):
        users = self.content['users']
        users.pop(username, None)
