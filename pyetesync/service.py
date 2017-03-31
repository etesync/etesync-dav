import requests
import json
import base64
import binascii
from furl import furl

from pyetesync.crypto import CryptoManager, HMAC_SIZE

API_PATH = ('api', 'v1')


class Authenticator:
    def __init__(self, remote):
        self.remote = furl(remote)
        self.remote.path.segments.extend(('api-token-auth', ''))
        self.remote.path.normalize()

    def get_auth_token(self, username, password):
        response = requests.post(self.remote.url, data={'username': username, 'password': password})
        data = response.json()
        return data['token']


class RawBase:
    def __init__(self, cryptoManager, content=None, uid=None):
        self.cryptoManager = cryptoManager
        self.uid = uid
        self.version = cryptoManager.version
        self.content = content

    def getContent(self):
        return self.cryptoManager.decrypt(self.content)

    def setContent(self, content):
        self.content = self.cryptoManager.encrypt(content)

    def to_simple(self):
        content = base64.b64encode(self.content)
        return {'uid': self.uid, 'content': content.decode()}


class RawJournal(RawBase):
    def __init__(self, cryptoManager, content=None, uid=None):
        super().__init__(cryptoManager, content, uid)
        if content is not None:
            self.hmac = content[:HMAC_SIZE]
            self.content = content[HMAC_SIZE:]

    def calcHmac(self):
        return self.cryptoManager.hmac(self.uid.encode() + self.content)

    def verify(self):
        if self.calcHmac() != self.hmac:
            raise Exception('HMAC MISMATCH')

    def to_simple(self):
        content = base64.b64encode(self.hmac + self.content)
        return {'uid': self.uid, 'content': content.decode(), 'version': self.version}

    def update(self, content):
        self.setContent(content)
        self.hmac = self.calcHmac()


class RawEntry(RawBase):
    def calcHmac(self, prev):
        prevUid = b''
        if prev is not None:
            prevUid = prev.uid.encode()

        return self.cryptoManager.hmac(prevUid + self.content)

    def verify(self, prev):
        if self.calcHmac(prev) != binascii.unhexlify(self.uid):
            raise Exception('HMAC MISMATCH')

    def update(self, content, prev):
        self.setContent(content)
        self.uid = binascii.hexlify(self.calcHmac(prev)).decode()


class BaseManager:
    def __init__(self, auth_token):
        self.headers = {'Authorization': 'Token ' + auth_token}

    def detail_url(self, uid):
        remote = self.remote.copy()
        remote.path.segments.extend((uid, ''))
        remote.path.normalize()
        return remote


class JournalManager(BaseManager):
    def __init__(self, remote, auth_token):
        super().__init__(auth_token)
        self.remote = furl(remote)
        self.remote.path.segments.extend(API_PATH + ('journals', ''))
        self.remote.path.normalize()

    def list(self, password):
        response = requests.get(self.remote.url, headers=self.headers)
        data = response.json()
        for j in data:
            uid = j['uid']
            version = j['version']
            content = base64.b64decode(j['content'])
            cryptoManager = CryptoManager(version, password, uid.encode())
            journal = RawJournal(cryptoManager=cryptoManager, content=content, uid=uid)
            yield journal

    def add(self, journal):
        data = journal.to_simple()
        requests.post(self.remote.url, headers=self.headers, json=data)

    def delete(self, journal):
        remote = self.detail_url(journal.uid)
        requests.delete(remote.url, headers=self.headers)

    def update(self, journal):
        remote = self.detail_url(journal.uid)
        data = journal.to_simple()
        requests.put(remote.url, headers=self.headers, json=data)


class EntryManager(BaseManager):
    def __init__(self, remote, auth_token, journalId):
        super().__init__(auth_token)
        self.remote = furl(remote)
        self.remote.path.segments.extend(API_PATH + ('journal', journalId, ''))
        self.remote.path.normalize()

    def list(self, cryptoManager, last=None):
        remote = self.remote.copy()
        prev = None
        if last is not None:
            prev = RawEntry(cryptoManager, b'', last)
            remote.args['last'] = last

        response = requests.get(remote.url, headers=self.headers)
        data = response.json()
        for j in data:
            uid = j['uid']
            content = base64.b64decode(j['content'])
            entry = RawEntry(cryptoManager=cryptoManager, content=content, uid=uid)
            entry.verify(prev)
            prev = entry
            yield entry

    def add(self, entries, last=None):
        remote = self.remote.copy()
        if last is not None:
            remote.args['last'] = last

        data = list(map(lambda x: x.to_simple(), entries))
        requests.post(remote.url, headers=self.headers, json=data)


class SyncEntry:
    def __init__(self, action, content):
        self.action = action
        self.content = content

    @classmethod
    def from_json(cls, json_string):
        data = json.loads(json_string)
        return SyncEntry(data['action'], data['content'])

    def to_json(self):
        data = {'action': self.action, 'content': self.content.decode()}
        return json.dumps(data, ensure_ascii=False)
