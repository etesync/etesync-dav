import json
import base64


class Credentials:
    def __init__(self, filename):
        self.filename = filename
        self.load()

    def load(self):
        with open(self.filename, "r") as f:
            self.content = json.load(f)

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(f, self.content)

    def get(self, username):
        users = self.content['users']
        user = users[username]
        return user['authToken'], base64.b64decode(user['cipherKey'])

    def set(self, username, auth_token, cipher_key):
        users = self.content['users']
        user = {
                'authToken': auth_token,
                'cipherKey': base64.b64encode(cipher_key),
            }
        users[username] = user

    def delete(self, username):
        users = self.content['users']
        users.pop(username, None)
