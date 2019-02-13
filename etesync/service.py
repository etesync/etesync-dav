import requests
import json
import base64
import binascii
from http import HTTPStatus
from furl import furl

from .crypto import CryptoManager, HMAC_SIZE
from . import exceptions

API_PATH = ('api', 'v1')


def _status_success(status_code):
    return status_code // 100 == 2


class Authenticator:
    def __init__(self, remote):
        self.remote = furl(remote)
        self.remote.path.segments.extend(('api-token-auth', ''))
        self.remote.path.normalize()

    def get_auth_token(self, username, password):
        response = requests.post(self.remote.url, data={'username': username, 'password': password})
        if response.status_code == HTTPStatus.BAD_REQUEST:
            raise exceptions.UnauthorizedException("Username or password incorrect.")
        elif not _status_success(response.status_code):
            raise exceptions.HttpException(response.status_code)

        data = response.json()
        return data['token']


class RawBase:
    def __init__(self, crypto_manager, content=None, uid=None):
        self.crypto_manager = crypto_manager
        self.uid = uid
        self.content = content

    @property
    def version(self):
        return self.crypto_manager.version

    def getContent(self):
        return self.crypto_manager.decrypt(self.content)

    def setContent(self, content):
        self.content = self.crypto_manager.encrypt(content)

    def to_simple(self):
        content = base64.b64encode(self.content)
        return {'uid': self.uid, 'content': content.decode()}

    def _verify_hmac(self, hmac1, hmac2):
        if hmac1 != hmac2:
            raise exceptions.IntegrityException("HMAC misatch: {} != {}".format(
                binascii.hexlify(hmac1).decode(), binascii.hexlify(hmac2).decode()))


class RawJournal(RawBase):
    def __init__(self, crypto_manager, content=None, uid=None, owner=None, encrypted_key=None, read_only=False):
        super().__init__(crypto_manager, content, uid)
        if content is not None:
            self.hmac = content[:HMAC_SIZE]
            self.content = content[HMAC_SIZE:]
        self.owner = owner
        self.encrypted_key = encrypted_key
        self.read_only = read_only

    def calc_hmac(self):
        return self.crypto_manager.hmac(self.uid.encode() + self.content)

    def verify(self):
        self._verify_hmac(self.hmac, self.calc_hmac())

    def to_simple(self):
        content = base64.b64encode(self.hmac + self.content)
        return {'uid': self.uid, 'content': content.decode(), 'version': self.version}

    def update(self, content):
        self.setContent(content)
        self.hmac = self.calc_hmac()


class RawEntry(RawBase):
    def calc_hmac(self, prev):
        prevUid = b''
        if prev is not None:
            prevUid = prev.uid.encode()

        return self.crypto_manager.hmac(prevUid + self.content)

    def verify(self, prev):
        self._verify_hmac(binascii.unhexlify(self.uid), self.calc_hmac(prev))

    def update(self, content, prev):
        self.setContent(content)
        self.uid = binascii.hexlify(self.calc_hmac(prev)).decode()


class RawUserInfo(RawBase):
    def __init__(self, crypto_manager, owner=None, pubkey=None, content=None):
        super().__init__(crypto_manager, content, None)
        self.owner = owner
        self.pubkey = pubkey
        if content is not None:
            self.hmac = content[:HMAC_SIZE]
            self.content = content[HMAC_SIZE:]

    def calc_hmac(self):
        return self.crypto_manager.hmac(self.content + self.pubkey)

    def verify(self):
        self._verify_hmac(self.hmac, self.calc_hmac())

    def to_simple(self):
        content = base64.b64encode(self.hmac + self.content)
        pubkey = base64.b64encode(self.pubkey)
        return {'owner': self.owner, 'pubkey': pubkey.decode(), 'content': content.decode(), 'version': self.version}

    def update(self, content):
        self.setContent(content)
        self.hmac = self.calc_hmac()


class BaseManager:
    def __init__(self, auth_token):
        headers = {'Authorization': 'Token ' + auth_token}
        self.requests = requests.Session()
        self.requests.headers.update(headers)

    def detail_url(self, uid):
        remote = self.remote.copy()
        remote.path.segments.extend((uid, ''))
        remote.path.normalize()
        return remote

    def _validate_response(self, response):
        if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
            raise exceptions.ServiceUnavailableException("Service unavailable")
        elif response.status_code == HTTPStatus.UNAUTHORIZED:
            raise exceptions.UnauthorizedException("UNAUTHORIZED auth token")
        elif response.status_code == HTTPStatus.FORBIDDEN:
            data = response.json()
            if data.get('code') == 'service_inactive':
                raise exceptions.UserInactiveException(data.get('detail'))
        elif response.status_code == HTTPStatus.NOT_FOUND:
            raise exceptions.HttpNotFound(response.status_code)
        elif not _status_success(response.status_code):
            raise exceptions.HttpException(response.status_code)
        return response


class JournalManager(BaseManager):
    def __init__(self, remote, auth_token):
        super().__init__(auth_token)
        self.remote = furl(remote)
        self.remote.path.segments.extend(API_PATH + ('journals', ''))
        self.remote.path.normalize()

    def list(self, password):
        response = self.requests.get(self.remote.url)
        self._validate_response(response)
        data = response.json()
        for j in data:
            uid = j['uid']
            version = j['version']
            content = base64.b64decode(j['content'])
            owner = j['owner']
            key = j['key']
            readOnly = j['readOnly']
            encrypted_key = base64.b64decode(key) if key is not None else None
            crypto_manager = CryptoManager(version, password, uid.encode())
            journal = RawJournal(crypto_manager=crypto_manager, content=content, uid=uid, owner=owner,
                                 encrypted_key=encrypted_key, read_only=readOnly)
            yield journal

    def add(self, journal):
        data = journal.to_simple()
        response = self.requests.post(self.remote.url, json=data)
        self._validate_response(response)

    def delete(self, journal):
        remote = self.detail_url(journal.uid)
        response = self.requests.delete(remote.url)
        self._validate_response(response)

    def update(self, journal):
        remote = self.detail_url(journal.uid)
        data = journal.to_simple()
        response = self.requests.put(remote.url, json=data)
        self._validate_response(response)

    # Members
    def _get_member_remote(self, journal, member_user=None):
        remote = self.detail_url(journal.uid).copy()
        segments = ['members']
        if member_user is not None:
            segments.append(member_user)
        segments.append('')
        remote.path.segments.extend(segments)
        remote.path.normalize()
        return remote

    def member_add(self, journal, member):
        remote = self._get_member_remote(journal)
        data = member.to_simple()
        response = self.requests.post(remote.url, json=data)
        self._validate_response(response)


class EntryManager(BaseManager):
    def __init__(self, remote, auth_token, journalId):
        super().__init__(auth_token)
        self.remote = furl(remote)
        self.remote.path.segments.extend(API_PATH + ('journals', journalId, 'entries', ''))
        self.remote.path.normalize()

    def list(self, crypto_manager, last=None):
        remote = self.remote.copy()
        prev = None
        if last is not None:
            prev = RawEntry(crypto_manager, b'', last)
            remote.args['last'] = last

        response = self.requests.get(remote.url)
        self._validate_response(response)
        data = response.json()
        for j in data:
            uid = j['uid']
            content = base64.b64decode(j['content'])
            entry = RawEntry(crypto_manager=crypto_manager, content=content, uid=uid)
            entry.verify(prev)
            prev = entry
            yield entry

    def add(self, entries, last=None):
        remote = self.remote.copy()
        if last is not None:
            remote.args['last'] = last

        data = list(map(lambda x: x.to_simple(), entries))
        response = self.requests.post(remote.url, json=data)
        self._validate_response(response)


class UserInfoManager(BaseManager):
    def __init__(self, remote, auth_token):
        super().__init__(auth_token)
        self.remote = furl(remote)
        self.remote.path.segments.extend(API_PATH + ('user', ''))
        self.remote.path.normalize()

    def get(self, owner, cipher_key):
        remote = self.detail_url(owner)
        response = self.requests.get(remote.url)
        self._validate_response(response)
        data = response.json()
        version = data['version']
        content = base64.b64decode(data['content'])
        pubkey = base64.b64decode(data['pubkey'])
        crypto_manager = CryptoManager(version, cipher_key, b"userInfo")
        return RawUserInfo(crypto_manager, owner, pubkey, content)

    def add(self, user_info):
        data = user_info.to_simple()
        response = self.requests.post(self.remote.url, json=data)
        self._validate_response(response)

    def delete(self, user_info):
        remote = self.detail_url(user_info.owner)
        response = self.requests.delete(remote.url)
        self._validate_response(response)

    def update(self, user_info):
        remote = self.detail_url(user_info.owner)
        data = user_info.to_simple()
        response = self.requests.put(remote.url, json=data)
        self._validate_response(response)


class SyncEntry:
    def __init__(self, action, content):
        self.action = action
        self.content = content

    @classmethod
    def from_json(cls, json_string):
        data = json.loads(json_string)
        return SyncEntry(data['action'], data['content'])

    def to_json(self):
        data = {'action': self.action, 'content': self.content}
        return json.dumps(data, ensure_ascii=False)


class Member:
    def __init__(self, user, key):
        self.user = user
        self.key = key

    def to_simple(self):
        key = base64.b64encode(self.key)
        return {'user': self.user, 'key': key.decode()}
