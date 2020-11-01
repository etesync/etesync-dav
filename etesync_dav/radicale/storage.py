# Copyright © 2017 Tom Hacohen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import logging
import re
from contextlib import contextmanager
import threading
import hashlib
import posixpath
import time

from .etesync_cache import etesync_for_user
from .href_mapper import HrefMapper

import etesync as api
from radicale import pathutils
from radicale.item import Item, get_etag
from radicale.storage import (
        BaseCollection, BaseStorage, ComponentNotFoundError,
    )
import vobject

from ..local_cache import Etebase, COL_TYPES
from .storage_etebase_collection import Collection as EtebaseCollection


logger = logging.getLogger('etesync-dav')


# How often we should sync automatically, in seconds
SYNC_INTERVAL = 15 * 60
# Minimum time to wait between syncs
SYNC_MINIMUM = 30


class SyncThread(threading.Thread):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._force_sync = threading.Event()
        self._done_syncing = threading.Event()
        self._done_syncing.set()  # We are done before we start.
        self.user = user
        self.last_sync = None
        self._exception = None

    def force_sync(self):
        self._force_sync.set()
        self._done_syncing.clear()

    def request_sync(self):
        if self.last_sync and time.time() - self.last_sync >= SYNC_MINIMUM:
            self.force_sync()

    @property
    def forced_sync(self):
        return self._force_sync.is_set()

    def wait_for_sync(self, timeout=None):
        ret = self._done_syncing.wait(timeout)
        e = self._exception
        self._exception = None
        if e is not None:
            raise e
        return ret

    def run(self):
        while True:
            try:
                with etesync_for_user(self.user) as (etesync, _):
                    self.last_sync = time.time()
                    self._done_syncing.clear()

                    etesync.sync()
            except Exception as e:
                # Print errors but keep on syncing in the background
                logger.exception(e)
                self._exception = e
            finally:
                self._force_sync.clear()
                self._done_syncing.set()

            self._force_sync.wait(SYNC_INTERVAL)


class MetaMapping:
    # Mappings between etesync meta and radicale
    _mappings = {
            "D:displayname": ("displayName", None, None),
        }

    @classmethod
    def _reverse_mapping(cls, mappings):
        mappings.update({i[1][0]: (i[0], i[1][1], i[1][2]) for i in mappings.items()})

    def _mapping_get(self, key):
        return self.__class__._mappings.get(key, (key, None, None))

    def map_get(self, info, key):
        key, get_transform, set_transform = self._mapping_get(key)
        value = info.get(key, None)
        if get_transform is not None:
            value = get_transform(value)

        if key == 'C:supported-calendar-component-set':
            return key, getattr(self, 'supported_calendar_component', 'none')

        return key, value

    def map_set(self, key, value):
        key, get_transform, set_transform = self._mapping_get(key)
        if set_transform is not None:
            value = set_transform(value)

        return key, value


def RgbToInt(str_color):
    if str_color is None:
        return None

    str_color = str_color[1:]
    color = int(str_color, 16)

    if len(str_color) == 8:  # RGBA
        alpha = color & 0xFF
        color = color >> 8
    else:
        alpha = 0xFF

    color |= alpha << 24
    return color


def IntToRgb(color):
    if color is None:
        return None

    blue = color & 0xFF
    green = (color >> 8) & 0xFF
    red = (color >> 16) & 0xFF
    alpha = (color >> 24) & 0xFF

    return '#%02x%02x%02x%02x' % (red, green, blue, alpha or 0xFF)


class MetaMappingCalendar(MetaMapping):
    supported_calendar_component = 'VEVENT'
    _mappings = MetaMapping._mappings.copy()
    _mappings.update({
            "C:calendar-description": ("description", None, None),
            "ICAL:calendar-color": ("color", IntToRgb, RgbToInt),
        })
    MetaMapping._reverse_mapping(_mappings)


class MetaMappingTaskList(MetaMappingCalendar):
    supported_calendar_component = 'VTODO'


class MetaMappingContacts(MetaMapping):
    _mappings = MetaMapping._mappings.copy()
    _mappings.update({
            "CR:addressbook-description": ("description", None, None),
        })
    MetaMapping._reverse_mapping(_mappings)


def _trim_suffix(path, suffixes):
    for suffix in suffixes:
        if path.endswith(suffix):
            path = path[:-len(suffix)]
            break

    return path


def _is_principal(path):
    sane_path = pathutils.sanitize_path(path).strip("/")
    attributes = sane_path.split("/")
    if not attributes[0]:
        attributes.pop()

    # It's a principal if all we have is the user
    return len(attributes) == 1


def _get_attributes_from_path(path):
    sane_path = pathutils.sanitize_path(path).strip("/")
    attributes = sane_path.split("/", 2)
    if not attributes[0]:
        attributes.pop()

    return attributes


VCARD_4_TO_3_PHOTO_URI_REGEX = re.compile(r'^(PHOTO|LOGO):http', re.MULTILINE)
VCARD_4_TO_3_PHOTO_INLINE_REGEX = re.compile(r'^(PHOTO|LOGO):data:image/([^;]*);base64,', re.MULTILINE)


class EteSyncItem(Item):
    def __init__(self, *args, **kwargs):
        """Initialize an item.

        ``collection_path`` the path of the parent collection (optional if
        ``collection`` is set).

        ``collection`` the parent collection (optional).

        ``href`` the href of the item.

        ``last_modified`` the HTTP-datetime of when the item was modified.

        ``text`` the text representation of the item (optional if
        ``vobject_item`` is set).

        ``vobject_item`` the vobject item (optional if ``text`` is set).

        ``etag`` the etag of the item (optional). See ``get_etag``.

        ``uid`` the UID of the object (optional). See ``get_uid_from_object``.

        ``name`` the name of the item (optional). See ``vobject_item.name``.

        ``component_name`` the name of the primary component (optional).
        See ``find_tag``.

        ``time_range`` the enclosing time range.
        See ``find_tag_and_time_range``.

        """
        self.etesync_item = kwargs.pop('etesync_item')
        super().__init__(*args, **kwargs)

    @property
    def etag(self):
        """Encoded as quoted-string (see RFC 2616)."""
        return get_etag(self.vobject_item.serialize())


class Collection(BaseCollection):
    def __init__(self, storage_, path):
        self._storage = storage_
        # Path should already be sanitized
        self._path = pathutils.sanitize_path(path).strip("/")

        attributes = _get_attributes_from_path(path)
        self.etesync = self._storage.etesync
        if len(attributes) == 2:
            self.uid = attributes[-1]
            self.journal = self.etesync.get(self.uid)
            self.collection = self.journal.collection
            if isinstance(self.collection, api.Calendar):
                self.tag = "VCALENDAR"
                self.meta_mappings = MetaMappingCalendar()
                self.content_suffix = ".ics"
            elif isinstance(self.collection, api.TaskList):
                self.tag = "VCALENDAR"
                self.meta_mappings = MetaMappingTaskList()
                self.content_suffix = ".ics"
            elif isinstance(self.collection, api.AddressBook):
                self.tag = "VADDRESSBOOK"
                self.meta_mappings = MetaMappingContacts()
                self.content_suffix = ".vcf"

            self.is_fake = False
        else:
            self.is_fake = True

        super().__init__()

    @property
    def path(self):
        return self._path

    @property
    def etag(self):
        """Encoded as quoted-string (see RFC 2616)."""
        if self.is_fake:
            return

        entry = None
        for entry in self.journal.list():
            pass

        return entry.uid if entry is not None else self.journal.uid

    def sync(self, old_token=None):
        """Get the current sync token and changed items for synchronization.

        ``old_token`` an old sync token which is used as the base of the
        delta update. If sync token is missing, all items are returned.
        ValueError is raised for invalid or old tokens.
        """
        token_prefix = 'http://radicale.org/ns/sync/'
        token = None  # XXX "{}{}".format(token_prefix, self.etag.strip('"'))
        if old_token is not None and old_token.startswith(token_prefix):
            old_token = old_token[len(token_prefix):]

        # FIXME: actually implement filtering by token
        return token, self._list()

    def _list(self):
        """List collection items."""
        if self.is_fake:
            return

        for item in self.collection.list():
            try:
                href_mapper = item._cache_obj.href.get()
            except HrefMapper.DoesNotExist:
                # Generate a new mapper
                href = hashlib.sha256(item.uid.encode()).hexdigest() + self.content_suffix
                href_mapper = HrefMapper(content=item._cache_obj, href=href)
                href_mapper.save(force_insert=True)

            href = href_mapper.href

            yield href

    def get_multi(self, hrefs):
        """Fetch multiple items.

        It's not required to return the requested items in the correct order.
        Duplicated hrefs can be ignored.

        Returns tuples with the href and the item or None if the item doesn't
        exist.

        """
        return ((href, self._get(href)) for href in hrefs)

    def get_all(self):
        """Fetch all items."""
        return (self._get(href) for href in self._list())

    def has_uid(self, uid):
        """Check if a UID exists in the collection."""
        for item in self.get_all():
            if item.uid == uid:
                return True
        return False

    def _get(self, href):
        """Fetch a single item."""
        if self.is_fake:
            return

        try:
            href_mapper = HrefMapper.get(HrefMapper.href == href)
            uid = href_mapper.content.uid
        except HrefMapper.DoesNotExist:
            return None

        etesync_item = self.collection.get(uid)

        try:
            item = vobject.readOne(etesync_item.content)
            # XXX Hack: fake transform 4.0 vCards to 3.0 as 4.0 is not yet widely supported
            if item.name == 'VCARD' and item.contents['version'][0].value == '4.0':
                # Don't do anything for groups as transforming them won't help anyway.
                if hasattr(item, 'kind') and item.kind.value.lower() == 'group':
                    pass
                else:
                    # XXX must be first because we are editing the content and reparsing
                    if 'photo' in item.contents:
                        content = etesync_item.content
                        content = VCARD_4_TO_3_PHOTO_URI_REGEX.sub(r'\1;VALUE=uri:', content)
                        content = VCARD_4_TO_3_PHOTO_INLINE_REGEX.sub(r'\1;ENCODING=b;TYPE=\2:', content)
                        item = vobject.readOne(content)
                        if content == etesync_item.content:
                            # Delete the PHOTO if we haven't managed to convert it
                            del item.contents['photo']

                    item.contents['version'][0].value = '3.0'
            # XXX Hack: add missing FN
            if item.name == 'VCARD' and not hasattr(item, 'fn'):
                item.add('fn').value = str(item.n)
        except Exception as e:
            raise RuntimeError("Failed to parse item %r in %r" %
                               (href, self.path)) from e
        last_modified = ''

        return EteSyncItem(collection=self, vobject_item=item, href=href, last_modified=last_modified,
                           etesync_item=etesync_item)

    def upload(self, href, vobject_item):
        """Upload a new or replace an existing item."""
        if self.is_fake:
            return

        content = vobject_item.serialize()

        item = self._get(href)
        if item is not None:
            etesync_item = item.etesync_item
            etesync_item.content = content
            etesync_item.save()
        else:
            etesync_item = self.collection.get_content_class().create(self.collection, content)
            etesync_item.save()
            href_mapper = HrefMapper(content=etesync_item._cache_obj, href=href)
            href_mapper.save(force_insert=True)

        return self._get(href)

    def delete(self, href=None):
        """Delete an item.

        When ``href`` is ``None``, delete the collection.

        """
        if self.is_fake:
            return

        if href is None:
            self.collection.delete()
            return

        item = self._get(href)
        if item is None:
            raise ComponentNotFoundError(href)

        item.etesync_item.delete()

    def get_meta(self, key=None):
        """Get metadata value for collection.

        Return the value of the property ``key``. If ``key`` is ``None`` return
        a dict with all properties

        """
        if self.is_fake:
            return {}

        if key == "tag":
            return self.tag
        elif key is None:
            ret = {}
            for key in self.journal.info.keys():
                ret[key] = self.meta_mappings.map_get(self.journal.info, key)[1]
            return ret
        else:
            key, value = self.meta_mappings.map_get(self.journal.info, key)
            return value

    def set_meta(self, _props):
        """Set metadata values for collection.

        ``props`` a dict with values for properties.

        """
        if self.is_fake:
            return

        props = {}
        for key, value in _props.items():
            key, value = self.meta_mappings.map_set(key, value)
            props[key] = value

        # Pop out tag which we don't want
        props.pop("tag", None)

        self.journal.update_info({})
        self.journal.update_info(props)
        self.journal.save()

    @property
    def last_modified(self):
        """Get the HTTP-datetime of when the collection was modified."""
        return ''


class Storage(BaseStorage):
    """Collection stored in several files per calendar."""

    _sync_thread_lock = threading.RLock()
    # Per-object lock for the "global" user and etesync
    _etesync_user_lock = None

    def __init__(self, configuration):
        self.user = None
        self.etesync = None
        self._etesync_user_lock = threading.RLock()
        super().__init__(configuration)

    def discover(self, path, depth="0"):
        """Discover a list of collections under the given ``path``.

        If ``depth`` is "0", only the actual object under ``path`` is
        returned.

        If ``depth`` is anything but "0", it is considered as "1" and direct
        children are included in the result.

        The ``path`` is relative.

        The root collection "/" must always exist.

        """

        if isinstance(self.etesync, Etebase):
            cls = EtebaseCollection
        else:
            cls = Collection

        # Path should already be sanitized
        attributes = _get_attributes_from_path(path)
        if len(attributes) == 3:
            if path.endswith('/'):
                # XXX Workaround UIDs with slashes in them - just continue as if path was one step above
                path = posixpath.join("/", attributes[0], attributes[1], "")
                attributes = _get_attributes_from_path(path)
            else:
                # XXX We would rather not rewrite urls, but we do it if urls contain /
                attributes[-1] = attributes[-1].replace('/', ',')
                path = posixpath.join("/", *attributes)

        try:
            if len(attributes) == 3:
                # If an item, create a collection for the item.
                item = attributes.pop()
                path = "/".join(attributes)
                collection = cls(self, path)
                yield collection._get(item)
                return

            collection = cls(self, path)
        except api.exceptions.DoesNotExist:
            return

        yield collection

        if depth == "0":
            return

        if len(attributes) == 0:
            yield cls(self, posixpath.join(path, cls.user))
        elif len(attributes) == 1:
            if isinstance(self.etesync, Etebase):
                for journal in self.etesync.list():
                    if journal.col_type in COL_TYPES:
                        yield cls(self, posixpath.join(path, journal.uid))
            else:
                for journal in self.etesync.list():
                    if journal.collection.TYPE in (api.AddressBook.TYPE, api.Calendar.TYPE, api.TaskList.TYPE):
                        yield cls(self, posixpath.join(path, journal.uid))
        elif len(attributes) == 2:
            for href in collection._list():
                yield collection._get(href)

        elif len(attributes) > 2:
            raise RuntimeError("Found more than one attribute. Shouldn't happen")

    def move(self, item, to_collection, to_href):
        """Move an object.

        ``item`` is the item to move.

        ``to_collection`` is the target collection.

        ``to_href`` is the target name in ``to_collection``. An item with the
        same name might already exist.

        """
        raise NotImplementedError

    def create_collection(self, href, items=None, props=None):
        """Create a collection.

        ``href`` is the sanitized path.

        If the collection already exists and neither ``collection`` nor
        ``props`` are set, this method shouldn't do anything. Otherwise the
        existing collection must be replaced.

        ``collection`` is a list of vobject components.

        ``props`` are metadata values for the collection.

        ``props["tag"]`` is the type of collection (VCALENDAR or
        VADDRESSBOOK). If the key ``tag`` is missing, it is guessed from the
        collection.

        """

        # We don't want to allow this
        raise NotImplementedError

    @contextmanager
    def acquire_lock(self, mode, user=None):
        """Set a context manager to lock the whole storage.

        ``mode`` must either be "r" for shared access or "w" for exclusive
        access.

        ``user`` is the name of the logged in user or empty.

        """
        if not user:
            return

        with etesync_for_user(user) as (etesync, _):
            with self.__class__._sync_thread_lock:
                if not hasattr(etesync, 'sync_thread'):
                    etesync.sync_thread = SyncThread(user, daemon=True)
                    etesync.sync_thread.start()
                else:
                    etesync.sync_thread.request_sync()

        # At most wait for 5 seconds before returning stale data
        etesync.sync_thread.wait_for_sync(5)

        with self._etesync_user_lock, etesync_for_user(user) as (etesync, _):
            self.user = user
            self.etesync = etesync

            yield

            # Always push changes if we made changes
            if mode == "w":
                etesync.sync_thread.force_sync()

            self.etesync = None
            self.user = None
