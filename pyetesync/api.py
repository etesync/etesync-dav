import vobject
import json
import os

from .crypto import CryptoManager, derive_key, CURRENT_VERSION
from .service import JournalManager, EntryManager, SyncEntry
from . import cache, pim, service, db, exceptions

API_URL = 'https://api.etesync.com/'

# Expose the authenticator
Authenticator = service.Authenticator


class EteSync:
    def __init__(self, email, auth_token, remote=API_URL, cipher_key=None, db_path=None):
        self.email = email
        self.auth_token = auth_token
        self.remote = remote
        self.cipher_key = cipher_key

        self._init_db(db_path)

        self.user, created = cache.User.get_or_create(username=email)

    def _init_db(self, db_path):
        from playhouse.sqlite_ext import SqliteExtDatabase

        if db_path is None:
            db_path = os.path.join(os.path.expanduser('~'), '.pyetesync', 'data.db')

        directory = os.path.dirname(db_path)
        if directory != '' and not os.path.exists(directory):
            os.makedirs(directory)

        database = SqliteExtDatabase(db_path)
        database.connect()

        db.database_proxy.initialize(database)

        self._init_db_tables(database)

    def _init_db_tables(self, database):
        database.create_tables([pim.Content, cache.User, cache.JournalEntity, cache.EntryEntity], safe=True)

    def sync(self):
        self.sync_journal_list()
        for journal in self.list():
            self.sync_journal(journal.uid)

    def sync_journal_list(self):
        self.push_journal_list()
        manager = JournalManager(self.remote, self.auth_token)

        existing = {}
        for journal in self.list():
            existing[journal.uid] = journal._cache_obj

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
        crypto_manager = CryptoManager(journal.version, self.cipher_key, journal_uid.encode())
        collection = Journal._from_cache(journal).collection

        prev = self._get_last_entry(journal)
        last_uid = None if prev is None else prev.uid

        for entry in manager.list(crypto_manager, last_uid):
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
            yield Journal._from_cache(cache_obj)

    def get(self, uid):
        try:
            return Journal._from_cache(self.user.journals.where(
                (cache.JournalEntity.uid == uid) & ~cache.JournalEntity.deleted).get())
        except cache.JournalEntity.DoesNotExist as e:
            raise exceptions.DoesNotExist(e)


class ApiObjectBase:
    def __init__(self):
        self._cache_obj = None

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.uid)

    @classmethod
    def _from_cache(cls, cache_obj):
        ret = cls()
        ret._cache_obj = cache_obj
        return ret

    @classmethod
    def create(cls, journal, uid, content):
        cache_obj = cls._CACHE_OBJ_CLASS()
        cache_obj.journal = journal._cache_obj
        cache_obj.uid = uid
        cache_obj.content = content
        cache_obj.new = True
        return cls._from_cache(cache_obj)

    @property
    def uid(self):
        return str(self._cache_obj.uid)

    @uid.setter
    def uid(self, uid):
        self._cache_obj.uid = uid

    @property
    def content(self):
        return self._cache_obj.content

    @content.setter
    def content(self, content):
        self._cache_obj.content = content


class Entry(ApiObjectBase):
    _CACHE_OBJ_CLASS = cache.EntryEntity

    def save(self):
        self._cache_obj.save()


class PimObject(ApiObjectBase):
    _CACHE_OBJ_CLASS = pim.Content

    @classmethod
    def create(cls, collection, uid, content):
        if collection.get_content_class() != cls:
            raise Exception('Collection "{}" does not allow "{}" children.'.format(
                collection.__class__.__name__, cls.__name__))
        return super().create(collection.journal, uid, content)

    def delete(self):
        self._cache_obj.deleted = True
        self._cache_obj.save()

    def save(self):
        self._cache_obj.dirty = True
        self._cache_obj.save()


class Event(PimObject):
    pass


class Contact(PimObject):
    pass


class BaseCollection:
    def __init__(self, journal):
        self._journal = journal
        self._cache_obj = journal._cache_obj
        if self._cache_obj.content is not None:
            self._journal_info = json.loads(self._cache_obj.content)
        else:
            self._journal_info = self._get_default_info()

    @property
    def display_name(self):
        return self._journal_info.get('displayName')

    @property
    def description(self):
        return self._journal_info.get('description')

    @property
    def journal(self):
        return self._journal

    def update_info(self, update_info):
        if update_info is None:
            self._journal_info = self._get_default_info()
        else:
            self._journal_info.update(update_info)
        self._cache_obj.content = json.dumps(self._journal_info, ensure_ascii=False)

    def _get_default_info(self):
        return {'type': self.__class__.TYPE, 'readOnly': False, 'selected': True}

    def apply_sync_entry(self, sync_entry):
        journal = self._cache_obj
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
        for content in self._cache_obj.content_set.where(~pim.Content.deleted):
            yield self.get_content_class()._from_cache(content)

    def get(self, uid):
        try:
            return self.get_content_class()._from_cache(self._cache_obj.content_set.where(pim.Content.uid == uid).get())
        except pim.Content.DoesNotExist as e:
            raise exceptions.DoesNotExist(e)

    @classmethod
    def create(cls, etesync, uid, content):
        cache_obj = cache.JournalEntity(new=True)
        cache_obj.owner = etesync.user
        cache_obj.uid = uid
        cache_obj.version = CURRENT_VERSION

        ret = cls(Journal._from_cache(cache_obj))
        ret.update_info(content)
        return ret

    def delete(self):
        self._cache_obj.deleted = True
        self._cache_obj.dirty = True
        self._cache_obj.save()

    def save(self):
        self._cache_obj.dirty = True
        self._cache_obj.save()


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
        return self._cache_obj.version

    @property
    def collection(self):
        journal_info = json.loads(self.content)
        if journal_info.get('type') == AddressBook.TYPE:
            return AddressBook(self)
        elif journal_info.get('type') == Calendar.TYPE:
            return Calendar(self)

    # CRUD
    def list(self):
        for entry in self._cache_obj.entries:
            yield Entry._from_cache(entry)
