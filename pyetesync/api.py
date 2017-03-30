from .crypto import CryptoManager, derive_key
from .service import JournalManager, EntryManager, SyncEntry, JournalInfo
from . import cache, pim, service

API_URL = 'https://api.etesync.com/'

# Expose the authenticator
Authenticator = service.Authenticator


class EteSync:
    def __init__(self, email, auth_token, remote=API_URL, cipher_key=None):
        self.email = email
        self.auth_token = auth_token
        self.remote = remote
        self.cipher_key = cipher_key

        self.user, created = cache.User.get_or_create(username=email)

    def sync(self):
        self.sync_journal_list()
        for journal in self.list():
            self.sync_journal(journal.uid)

    def sync_journal_list(self):
        manager = JournalManager(self.remote, self.auth_token)

        existing = {}
        for journal in self.list():
            existing[journal.uid] = journal.cache_obj

        for entry in manager.list(self.cipher_key):
            entry.verify()
            if entry.uid in existing:
                journal = existing[entry.uid]
                del existing[journal.uid]
            else:
                journal = cache.JournalEntity(owner=self.user, version=entry.version, uid=entry.uid)
            journal.content = entry.getContent()
            journal.save()

        # Delete remaining
        for journal in existing.values():
            journal.deleted = True
            journal.save()

    def sync_journal(self, uid):
        journal_uid = uid
        manager = EntryManager(self.remote, self.auth_token, journal_uid)

        journal = cache.JournalEntity.get(uid=journal_uid)
        cryptoManager = CryptoManager(journal.version, self.cipher_key, journal_uid.encode('utf-8'))
        collection = Journal(journal).collection

        try:
            prev = journal.entries.order_by(cache.EntryEntity.id.desc()).get()
            last_uid = prev.uid
        except cache.EntryEntity.DoesNotExist:
            prev = None
            last_uid = None

        for entry in manager.list(cryptoManager, last_uid):
            entry.verify(prev)
            syncEntry = SyncEntry.from_json(entry.getContent().decode())
            collection.apply_sync_entry(syncEntry)
            cache.EntryEntity.create(uid=entry.uid, content=entry.getContent(), journal=journal)

            prev = entry

    def derive_key(self, password):
        self.cipher_key = derive_key(password, self.email)
        return self.cipher_key

    # CRUD operations
    def list(self):
        for cache_journal in cache.JournalEntity.select().where(~cache.JournalEntity.deleted):
            yield Journal(cache_journal)

    def get(self, uid):
        return Journal(cache.JournalEntity.get(uid=uid, deleted=False))


class ApiObjectBase:
    def __init__(self, cache_obj):
        self.cache_obj = cache_obj

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.uid)

    @property
    def uid(self):
        return self.cache_obj.uid

    @property
    def content(self):
        return self.cache_obj.content


class Entry(ApiObjectBase):
    pass


class Event(ApiObjectBase):
    pass


class Contact(ApiObjectBase):
    pass


class BaseCollection:
    def __init__(self, journal, journal_info):
        self.cache_journal = journal.cache_obj
        self.journal_info = journal_info

    @property
    def display_name(self):
        return self.journal_info.display_name

    @property
    def description(self):
        return self.journal_info.description


class Calendar(BaseCollection):
    def apply_sync_entry(self, sync_entry):
        pim.Event.apply_sync_entry(self.cache_journal, sync_entry)

    # CRUD
    def list(self):
        for event in self.cache_journal.event_set:
            yield Event(event)

    def get(self, uid):
        return Event(self.cache_journal.event_set.where(pim.Event.uid == uid).get())


class AddressBook(BaseCollection):
    def apply_sync_entry(self, sync_entry):
        pim.Contact.apply_sync_entry(self.cache_journal, sync_entry)

    # CRUD
    def list(self):
        for contact in self.cache_journal.contact_set:
            yield Contact(contact)

    def get(self, uid):
        return Contact(self.cache_journal.contact_set.where(pim.Contact.uid == uid).get())


class Journal(ApiObjectBase):
    @property
    def version(self):
        return self.cache_obj.version

    @property
    def collection(self):
        journal_info = JournalInfo.from_json(self.content)
        if journal_info.journal_type == 'ADDRESS_BOOK':
            return AddressBook(self, journal_info)
        elif journal_info.journal_type == 'CALENDAR':
            return Calendar(self, journal_info)

    # CRUD
    def list(self):
        for entry in self.cache_obj.entries:
            yield Entry(entry)
