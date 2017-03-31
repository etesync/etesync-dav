import vobject
import json

from .crypto import CryptoManager, derive_key, CURRENT_VERSION
from .service import JournalManager, EntryManager, SyncEntry
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
        self.push_journal_list()
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

    def push_journal_list(self):
        manager = JournalManager(self.remote, self.auth_token)

        changed = self.user.journals.where(cache.JournalEntity.dirty | cache.JournalEntity.new)

        for journal in changed:
            crypto_manager = CryptoManager(journal.version, self.cipher_key, journal.uid.encode())
            raw_journal = service.RawJournal(crypto_manager, uid=journal.uid)
            raw_journal.update(journal.content)

            if journal.deleted:
                manager.delete(raw_journal)
            elif journal.new:
                manager.add(raw_journal)
                journal.new = False
            else:
                manager.update(raw_journal)

            journal.dirty = False
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
        cryptoManager = CryptoManager(journal.version, self.cipher_key, journal_uid.encode())
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
        crypto_manager = CryptoManager(journal.version, self.cipher_key, journal_uid.encode())
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
        for cache_obj in self.user.journals.where(~cache.JournalEntity.deleted):
            yield Journal(cache_obj)

    def get(self, uid):
        return Journal(self.user.journals.where((cache.JournalEntity.uid == uid) & ~cache.JournalEntity.deleted).get())


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
    def __init__(self, journal):
        self.cache_obj = journal.cache_obj
        if self.cache_obj.content is not None:
            self.journal_info = json.loads(self.cache_obj.content)
        else:
            self.journal_info = self._get_default_info()

    @property
    def display_name(self):
        return self.journal_info.get('displayName')

    @property
    def description(self):
        return self.journal_info.get('description')

    def update_info(self, update_info):
        if update_info is None:
            self.journal_info = self._get_default_info()
        else:
            self.journal_info.update(update_info)
        self.cache_obj.content = json.dumps(self.journal_info, ensure_ascii=False)

    def _get_default_info(self):
        return {'type': self.__class__.TYPE, 'readOnly': False, 'selected': True}

    def apply_sync_entry(self, sync_entry):
        journal = self.cache_obj
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
        for content in self.cache_obj.content_set.where(~pim.Content.deleted):
            yield self.get_content_class()(content)

    def get(self, uid):
        return self.get_content_class()(self.cache_obj.content_set.where(pim.Content.uid == uid).get())

    @classmethod
    def create(cls, etesync, uid, content):
        cache_obj = cache.JournalEntity(new=True)
        cache_obj.owner = etesync.user
        cache_obj.uid = uid
        cache_obj.version = CURRENT_VERSION

        ret = cls(Journal(cache_obj))
        ret.update_info(content)
        cache_obj.save()
        return ret

    def delete(self):
        self.cache_obj.deleted = True
        self.cache_obj.dirty = True
        self.cache_obj.save()

    def save(self):
        self.cache_obj.dirty = True
        self.cache_obj.save()


class Calendar(BaseCollection):
    TYPE = 'CALENDAR'

    def get_uid(self, sync_entry):
        vobj = vobject.readOne(sync_entry.content)
        return vobj.vevent.uid.value

    def get_content_class(self):
        return Event

    def _get_default_info(self):
        ret = super()._get_default_info()
        ret.update({'supportsVEVENT': True})
        return ret


class AddressBook(BaseCollection):
    TYPE = 'ADDRESS_BOOK'

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
        journal_info = json.loads(self.content)
        if journal_info.get('type') == AddressBook.TYPE:
            return AddressBook(self)
        elif journal_info.get('type') == Calendar.TYPE:
            return Calendar(self)

    # CRUD
    def list(self):
        for entry in self.cache_obj.entries:
            yield Entry(entry)
