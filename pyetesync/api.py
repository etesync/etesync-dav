import vobject

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
        # FIXME: At the moment if there's a conflict remote would win, which is
        # not good and doesn't conform to java client. Copy what's done there.
        self.pull_journal(uid)
        self.push_journal(uid)

    def _get_last_entry(self, journal):
        try:
            return journal.entries.order_by(cache.EntryEntity.id.desc()).get()
        except cache.EntryEntity.DoesNotExist:
            return None

    def pull_journal(self, uid):
        journal_uid = uid
        manager = EntryManager(self.remote, self.auth_token, journal_uid)

        journal = cache.JournalEntity.get(uid=journal_uid)
        cryptoManager = CryptoManager(journal.version, self.cipher_key, journal_uid.encode('utf-8'))
        collection = Journal(journal).collection

        prev = self._get_last_entry(journal)
        last_uid = None if prev is None else prev.uid

        for entry in manager.list(cryptoManager, last_uid):
            entry.verify(prev)
            syncEntry = SyncEntry.from_json(entry.getContent().decode())
            collection.apply_sync_entry(syncEntry)
            cache.EntryEntity.create(uid=entry.uid, content=entry.getContent(), journal=journal)

            prev = entry

    def push_journal(self, uid):
        # FIXME: Implement pushing in chunks
        journal_uid = uid
        manager = EntryManager(self.remote, self.auth_token, journal_uid)

        journal = cache.JournalEntity.get(uid=journal_uid)
        crypto_manager = CryptoManager(journal.version, self.cipher_key, journal_uid.encode('utf-8'))
        changed_set = journal.content_set.where(pim.Content.new | pim.Content.dirty | pim.Content.deleted)
        changed = list(changed_set)

        if len(changed) == 0:
            return

        prev = self._get_last_entry(journal)
        last_uid = None if prev is None else prev.uid

        entries = []
        for pim_entry in changed:
            if pim_entry.deleted:
                action = 'DELETE'
            elif pim_entry.new:
                action = 'ADD'
            else:
                action = 'CHANGE'
            sync_entry = SyncEntry(action, pim_entry.content)
            raw_entry = service.RawEntry(crypto_manager)
            raw_entry.update(sync_entry.to_json(), prev)
            entries.append(raw_entry)

        manager.add(entries, last_uid)

        # Add entries to cache
        for entry in entries:
            cache.EntryEntity.create(uid=entry.uid, content=entry.getContent(), journal=journal)

        # Clear dirty flags and delete deleted content
        pim.Content.delete().where((pim.Content.journal == journal) & pim.Content.deleted).execute()
        pim.Content.update(new=False, dirty=False).where(
                (pim.Content.journal == journal) & (pim.Content.new | pim.Content.dirty)
            ).execute()

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

    @uid.setter
    def uid(self, uid):
        self.cache_obj.uid = uid

    @property
    def content(self):
        return self.cache_obj.content

    @content.setter
    def content(self, content):
        self.cache_obj.content = content


class Entry(ApiObjectBase):
    pass


class PimObject(ApiObjectBase):
    @classmethod
    def create(cls, journal, uid, content):
        cache_obj = pim.Content()
        cache_obj.journal = journal.cache_obj
        cache_obj.uid = uid
        cache_obj.content = content
        cache_obj.new = True
        cache_obj.save()
        return cls(cache_obj)

    def delete(self):
        self.cache_obj.deleted = True
        self.cache_obj.save()

    def save(self):
        self.cache_obj.dirty = True
        self.cache_obj.save()


class Event(PimObject):
    pass


class Contact(PimObject):
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

    def apply_sync_entry(self, sync_entry):
        journal = self.cache_journal
        uid = self.get_uid(sync_entry)

        try:
            content = pim.Content.get(uid=uid, journal=journal)
        except pim.Content.DoesNotExist:
            content = None

        if sync_entry.action == 'DELETE':
            if content is not None:
                content.delete_instance()
            else:
                print("WARNING: Failed to delete " + uid)

            return

        content = pim.Content(journal=journal, uid=uid) if content is None else content

        content.content = sync_entry.content
        content.save()

    # CRUD
    def list(self):
        for content in self.cache_journal.content_set.where(~pim.Content.deleted):
            yield self.get_content_class()(content)

    def get(self, uid):
        return self.get_content_class(self.cache_journal.event_set.where(pim.Content.uid == uid).get())


class Calendar(BaseCollection):
    def get_uid(self, sync_entry):
        vobj = vobject.readOne(sync_entry.content)
        return vobj.vevent.uid.value

    def get_content_class(self):
        return Event


class AddressBook(BaseCollection):
    def get_uid(self, sync_entry):
        vobj = vobject.readOne(sync_entry.content)
        return vobj.uid.value

    def get_content_class(self):
        return Contact


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
