from urllib.request import build_opener
import urllib.parse
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
        details = urllib.parse.urlencode({'username': username, 'password': password}).encode('utf-8')
        request = urllib.request.Request(self.remote.url, details)
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode())
        return data['token']


class RawBase:
    def __init__(self, cryptoManager, content, uid):
        self.cryptoManager = cryptoManager
        self.uid = uid
        self.version = cryptoManager.version
        self.content = content

    def getContent(self):
        return self.cryptoManager.decrypt(self.content)


class RawJournal(RawBase):
    def __init__(self, cryptoManager, content, uid):
        super().__init__(cryptoManager, content, uid)
        self.hmac = content[:HMAC_SIZE]
        self.content = content[HMAC_SIZE:]

    def calcHmac(self):
        return self.cryptoManager.hmac(self.uid.encode('utf-8') + self.content)

    def verify(self):
        if self.calcHmac() != self.hmac:
            raise Exception('HMAC MISMATCH')


class RawEntry(RawBase):
    def calcHmac(self, prev):
        prevUid = b''
        if prev is not None:
            prevUid = prev.uid.encode('utf-8')

        return self.cryptoManager.hmac(prevUid + self.content)

    def verify(self, prev):
        if self.calcHmac(prev) != binascii.unhexlify(self.uid):
            raise Exception('HMAC MISMATCH')


class BaseManager:
    def __init__(self, remote, authToken):
        self.remote = furl(remote)
        self.remote.path.segments.extend(API_PATH + ('journals', ''))
        self.remote.path.normalize()
        self.opener = build_opener()
        self.opener.addheaders = [('Authorization', 'Token ' + authToken)]

    def list(self, password):
        response = self.opener.open(self.remote.url)
        data = json.loads(response.read().decode())
        for j in data:
            uid = j['uid']
            version = j['version']
            content = base64.b64decode(j['content'])
            cryptoManager = CryptoManager(version, password, uid.encode('utf-8'))
            journal = RawJournal(cryptoManager=cryptoManager, content=content, uid=uid)
            yield journal


class JournalManager:
    def __init__(self, remote, authToken):
        self.remote = furl(remote)
        self.remote.path.segments.extend(API_PATH + ('journals', ''))
        self.remote.path.normalize()
        self.opener = build_opener()
        self.opener.addheaders = [('Authorization', 'Token ' + authToken)]

    def list(self, password):
        response = self.opener.open(self.remote.url)
        data = json.loads(response.read().decode())
        for j in data:
            uid = j['uid']
            version = j['version']
            content = base64.b64decode(j['content'])
            cryptoManager = CryptoManager(version, password, uid.encode('utf-8'))
            journal = RawJournal(cryptoManager=cryptoManager, content=content, uid=uid)
            yield journal


class EntryManager:
    def __init__(self, remote, authToken, journalId):
        self.remote = furl(remote)
        self.remote.path.segments.extend(API_PATH + ('journal', journalId, ''))
        self.remote.path.normalize()
        self.opener = build_opener()
        self.opener.addheaders = [('Authorization', 'Token ' + authToken)]

    def list(self, cryptoManager, last=None):
        remote = self.remote.copy()
        prev = None
        if last is not None:
            prev = RawEntry(cryptoManager, b'', last)
            remote.args['last'] = last
        response = self.opener.open(remote.url)
        data = json.loads(response.read().decode())
        for j in data:
            uid = j['uid']
            content = base64.b64decode(j['content'])
            entry = RawEntry(cryptoManager=cryptoManager, content=content, uid=uid)
            entry.verify(prev)
            prev = entry
            yield entry


class SyncEntry:
    def __init__(self, action, content):
        self.action = action
        self.content = content

    @classmethod
    def from_json(cls, json_string):
        data = json.loads(json_string)
        return SyncEntry(data['action'], data['content'])


class JournalInfo:
    def __init__(self, journal_type, display_name, description):
        self.journal_type = journal_type
        self.display_name = display_name
        self.description = description

    @classmethod
    def from_json(cls, json_string):
        data = json.loads(json_string)
        return JournalInfo(data['type'], data.get('displayName', ''), data.get('description', ''))
