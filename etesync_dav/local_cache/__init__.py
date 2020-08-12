import os

import msgpack

from etebase import Account, Client, FetchOptions, ItemMetadata
from etesync_dav import config

from . import db, models


class StorageException(Exception):
    pass


class DoesNotExist(StorageException):
    pass


def msgpack_encode(content):
    return msgpack.packb(content, use_bin_type=True)


def msgpack_decode(content):
    return msgpack.unpackb(content, raw=False)


def batch(iterable, n=1):
    length = len(iterable)
    for ndx in range(0, length, n):
        yield iterable[ndx:min(ndx + n, length)]


def get_millis():
    import time
    return int(round(time.time() * 1000))


class Etebase:
    def __init__(self, username, stored_session, remote_url=None):
        db_path = config.ETEBASE_DATABASE_FILE
        client = Client.new("etesync-dav", remote_url)
        self.etebase = Account.restore(client, stored_session, None)
        self.username = username

        self._init_db(db_path)

    def reinit(self):
        self._set_db(self._database)

    def _set_db(self, database):
        self._database = database

        db.database_proxy.initialize(database)

        self._init_db_tables(database)

        self.user, created = models.User.get_or_create(username=self.username)

    def _init_db(self, db_path):
        from playhouse.sqlite_ext import SqliteExtDatabase

        directory = os.path.dirname(db_path)
        if directory != '' and not os.path.exists(directory):
            os.makedirs(directory)

        database = SqliteExtDatabase(db_path, pragmas={
            'journal_mode': 'wal',
            'foreign_keys': 1,
            })
        database.connect()

        self._set_db(database)

    def _init_db_tables(self, database, additional_tables=None):
        CURRENT_DB_VERSION = 0

        database.create_tables([models.Config, models.User, models.CollectionEntity,
                                models.ItemEntity, models.HrefMapper], safe=True)
        if additional_tables:
            database.create_tables(additional_tables, safe=True)

        default_db_version = CURRENT_DB_VERSION
        config, created = models.Config.get_or_create(defaults={'db_version': default_db_version})

    def sync(self):
        self.sync_collection_list()
        for collection in self.list():
            self.sync_collection(collection.uid)

    def sync_collection_list(self):
        self.push_collection_list()

        col_mgr = self.etebase.get_collection_manager()
        stoken = self.user.stoken
        done = False

        while not done:
            fetch_options = FetchOptions()
            fetch_options.stoken(stoken)
            col_list = col_mgr.list(fetch_options)
            for col in col_list.get_data():
                collection = models.CollectionEntity.get_or_none(local_user=self.user, uid=col.get_uid())
                if collection is None:
                    collection = models.CollectionEntity(
                        local_user=self.user,
                        uid=col.get_uid(),
                    )
                collection.eb_col = bytes(col_mgr.cache_save_with_content(col))
                collection.stoken = col.get_stoken()
                collection.deleted = col.is_deleted()
                collection.save()

            for col_uid in col_list.get_removed_memberships():
                try:
                    collection = models.CollectionEntity.get(local_user=self.user, uid=col_uid)
                    collection.deleted = True
                    collection.save()
                except models.CollectionEntity.DoesNotExist:
                    # Already removed
                    pass

            done = col_list.is_done()
            stoken = col_list.get_stoken()

            self.user.stoken = stoken
            self.user.save()

    def _collection_list_dirty_get(self):
        return self.user.collections.where(models.CollectionEntity.dirty | models.CollectionEntity.new)

    def collection_list_is_dirty(self):
        changed = list(self._collection_list_dirty_get())
        return len(changed) > 0

    def push_collection_list(self):
        col_mgr = self.etebase.get_collection_manager()

        changed = self._collection_list_dirty_get()

        for collection in changed:
            col = col_mgr.cache_load(changed.eb_col)
            col.set_meta_raw(changed.meta)

            if collection.deleted:
                col.delete()
            col_mgr.upload(col, None)

            collection.dirty = False
            collection.save()

    def sync_collection(self, uid):
        self.push_collection(uid)
        self.pull_collection(uid)

    def pull_collection(self, uid):
        col_mgr = self.etebase.get_collection_manager()
        cache_col = models.CollectionEntity.get(local_user=self.user, uid=uid)
        if cache_col.stoken == cache_col.local_stoken:
            return

        col = col_mgr.cache_load(cache_col.eb_col)
        item_mgr = col_mgr.get_item_manager(col)
        stoken = cache_col.local_stoken
        done = False

        while not done:
            fetch_options = FetchOptions()
            fetch_options.stoken(stoken)
            item_list = item_mgr.list(fetch_options)

            for item in item_list.get_data():
                meta = msgpack_decode(bytes(item.get_meta_raw()))
                cache_item = models.ItemEntity.get_or_none(collection=cache_col, uid=meta["name"])
                if cache_item is None:
                    cache_item = models.ItemEntity(
                        collection=cache_col,
                        uid=meta["name"],
                    )
                cache_item.eb_item = bytes(item_mgr.cache_save_with_content(item))
                cache_item.deleted = item.is_deleted()
                cache_item.save()

            done = item_list.is_done()
            stoken = item_list.get_stoken()

            cache_col.local_stoken = stoken
            cache_col.save()

    def _collection_dirty_get(self, collection):
        return collection.items.where(models.ItemEntity.dirty | models.ItemEntity.new)

    def collection_is_dirty(self, uid):
        cache_col = models.CollectionEntity.get(local_user=self.user, uid=uid)
        changed = list(self._collection_dirty_get(cache_col))
        return len(changed) > 0

    def push_collection(self, uid):
        CHUNK_PUSH = 30
        col_mgr = self.etebase.get_collection_manager()
        cache_col = models.CollectionEntity.get(local_user=self.user, uid=uid)
        col = col_mgr.cache_load(cache_col.eb_col)
        item_mgr = col_mgr.get_item_manager(col)

        changed = self._collection_dirty_get(cache_col)

        for chunk in batch(changed, CHUNK_PUSH):
            chunk_items = list(map(lambda x: item_mgr.cache_load(x.eb_item), chunk))
            item_mgr.batch(chunk_items, None, None)
            for cache_item, item in zip(chunk, chunk_items):
                cache_item.eb_item = bytes(item_mgr.cache_save(item))
                cache_item.dirty = False
                cache_item.new = False
                cache_item.save()

    # CRUD operations
    def list(self):
        col_mgr = self.etebase.get_collection_manager()
        for cache_obj in self.user.collections.where(~models.CollectionEntity.deleted):
            yield Collection(col_mgr, cache_obj)

    def get(self, uid):
        col_mgr = self.etebase.get_collection_manager()
        try:
            return Collection(col_mgr, self.user.collections.where(
                (models.CollectionEntity.uid == uid) & ~models.CollectionEntity.deleted).get())
        except models.CollectionEntity.DoesNotExist as e:
            raise DoesNotExist(e)


class Collection:
    def __init__(self, col_mgr, cache_col):
        self.col_mgr = col_mgr
        self.cache_col = cache_col
        self.col = col_mgr.cache_load(cache_col.eb_col)

    @property
    def uid(self):
        return self.col.get_uid()

    @property
    def read_only(self):
        return self.col.get_access_level() == "ro"

    @property
    def stoken(self):
        return self.cache_col.local_stoken

    @property
    def col_type(self):
        return self.meta['type']

    # FIXME: cache
    @property
    def meta(self):
        return msgpack_decode(bytes(self.col.get_meta_raw()))

    def update_meta(self, update_info):
        if update_info is None:
            raise RuntimeError("update_info can't be None.")
        meta = self.meta
        meta.update(update_info)
        self.col.set_meta_raw(msgpack_encode(meta))
        self.cache_col.eb_col = bytes(self.col_mgr.cache_save(self.col))
        self.cache_col.save()

    # CRUD
    def create(self, vobject_item):
        item_mgr = self.col_mgr.get_item_manager(self.col)
        item_meta = ItemMetadata()
        item_meta.set_name(vobject_item.uid)
        item_meta.set_mtime(get_millis())
        item = item_mgr.create(item_meta, vobject_item.serialize().encode())
        cache_item = models.ItemEntity(collection=self.cache_col, uid=vobject_item.uid)
        cache_item.eb_item = bytes(item_mgr.cache_save_with_content(item))
        cache_item.deleted = item.is_deleted()
        cache_item.new = True
        return Item(item_mgr, cache_item)

    def get(self, uid):
        item_mgr = self.col_mgr.get_item_manager(self.col)
        return Item(item_mgr,
                    self.cache_col.items.where((models.ItemEntity.uid == uid) & ~models.ItemEntity.deleted).get())

    def list(self):
        item_mgr = self.col_mgr.get_item_manager(self.col)
        for cache_item in self.cache_col.items.where(~models.ItemEntity.deleted):
            yield Item(item_mgr, cache_item)


class Item:
    def __init__(self, item_mgr, cache_item):
        self.item_mgr = item_mgr
        self.cache_item = cache_item
        self.item = item_mgr.cache_load(cache_item.eb_item)

    @property
    def uid(self):
        return self.meta['name']

    # FIXME: cache
    @property
    def meta(self):
        return msgpack_decode(bytes(self.item.get_meta_raw()))

    @meta.setter
    def meta(self, meta):
        self.item.set_meta_raw(msgpack_encode(meta))

    # FIXME: cache
    @property
    def content(self):
        return bytes(self.item.get_content()).decode()

    @property
    def etag(self):
        return self.item.get_etag()

    @content.setter
    def content(self, content):
        self.item.set_content(content.encode())

    def delete(self):
        self.item.delete()
        self.cache_item.deleted = True
        self.save()

    def save(self):
        item_meta = self.meta
        item_meta["mtime"] = get_millis()
        self.meta = item_meta
        self.cache_item.eb_item = bytes(self.item_mgr.cache_save(self.item))
        self.cache_item.dirty = True
        self.cache_item.save()
