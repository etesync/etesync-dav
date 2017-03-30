from .crypto import CryptoManager, derive_key
from .service import JournalManager, EntryManager, SyncEntry, JournalInfo
from . import cache, pim

API_URL = 'https://api.etesync.com/'


class EteSync:
    def __init__(self, email, auth_token, remote=API_URL):
        self.email = email
        self.auth_token = auth_token
        self.remote = remote

        self.user, created = cache.User.get_or_create(username=email)

    def sync(self):
        self.sync_journal_list()
        for journal in self.list():
            self.sync_journal(journal.uid)

    def sync_journal_list(self):
        manager = JournalManager(self.remote, self.auth_token)

        # FIXME: Handle deletions on server
        for entry in manager.list(self.cipher_key):
            entry.verify()
            try:
                journal = cache.JournalEntity.get(uid=entry.uid)
            except cache.JournalEntity.DoesNotExist:
                journal = cache.JournalEntity(owner=self.user, version=entry.version, uid=entry.uid)
            journal.content = entry.getContent()
            journal.save()

    def sync_journal(self, uid):
        journal_uid = uid
        manager = EntryManager(self.remote, self.auth_token, journal_uid)

        journal = cache.JournalEntity.get(uid=journal_uid)
        cryptoManager = CryptoManager(journal.version, self.cipher_key, journal_uid.encode('utf-8'))
        journalInfo = JournalInfo.from_json(journal.content)

        try:
            last = journal.entries.order_by(cache.EntryEntity.id.desc()).get().uid
        except cache.EntryEntity.DoesNotExist:
            last = None

        prev = None
        for entry in manager.list(cryptoManager, last):
            entry.verify(prev)
            syncEntry = SyncEntry.from_json(entry.getContent().decode())
            if journalInfo.journal_type == 'ADDRESS_BOOK':
                pim.Contact.apply_sync_entry(journal, syncEntry)
            elif journalInfo.journal_type == 'CALENDAR':
                pim.Event.apply_sync_entry(journal, syncEntry)
            cache.EntryEntity.create(uid=entry.uid, content=entry.getContent(), journal=journal)

            prev = entry

    def derive_key(self, password):
        self.cipher_key = derive_key(password, self.email)
        return self.cipher_key

    # CRUD operations
    def list(self):
        for cache_journal in cache.JournalEntity.select():
            yield Journal(cache_journal)

    def get(self, uid):
        return Journal(cache.JournalEntity.get(uid=uid))


class ApiObjectBase:
    def __init__(self, cache_obj):
        self.cache_obj = cache_obj

    @property
    def uid(self):
        return self.cache_obj.uid

    @property
    def content(self):
        return self.cache_obj.content


class Entry(ApiObjectBase):
    pass


class Journal(ApiObjectBase):
    @property
    def version(self):
        return self.cache_obj.version

    @property
    def entries(self):
        for entry in self.cache_obj.entries:
            yield Entry(entry)
