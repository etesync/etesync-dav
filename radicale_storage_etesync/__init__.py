from contextlib import contextmanager
import hashlib
import posixpath
import time
from uuid import uuid4

from .etesync_cache import EteSyncCache
from .href_mapper import HrefMapper

import etesync as api
from radicale.storage import (
        BaseCollection, sanitize_path, Item, ComponentNotFoundError, get_etag, UnsafePathError, groupby, get_uid
    )
import vobject


CONFIG_SECTION = "storage"


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
            return key, getattr(self, 'supported_calendar_component', None)

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
    sane_path = sanitize_path(path).strip("/")
    attributes = sane_path.split("/")
    if not attributes[0]:
        attributes.pop()

    # It's a principal if all we have is the user
    return len(attributes) == 1


def _get_attributes_from_path(path):
    sane_path = sanitize_path(path).strip("/")
    attributes = sane_path.split("/", 2)
    if not attributes[0]:
        attributes.pop()

    return attributes


class PrincipalNotAllowedError(UnsafePathError):
    def __init__(self, path):
        message = "Creating a principal collection is not allowed: %r" % path
        super().__init__(message)


class EteSyncItem(Item):
    def __init__(self, collection, item, href, last_modified=None, etesync_item=None):
        super().__init__(collection, item, href, last_modified)
        self.etesync_item = etesync_item

    @property
    def etag(self):
        """Encoded as quoted-string (see RFC 2616)."""
        return get_etag(self.item.serialize())


class Collection(BaseCollection):
    """Collection stored in several files per calendar."""

    def __init__(self, path, principal=False, folder=None, tag=None):
        attributes = _get_attributes_from_path(path)
        self.etesync = self.__class__.etesync
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

            if tag is not None and tag != self.tag:
                raise RuntimeError("Tag mismatch")

            self.is_fake = False
        else:
            self.is_fake = True

        # Needed by Radicale
        self.path = sanitize_path(path).strip("/")

    @classmethod
    def static_init(cls):
        cls._etesync_cache = None

    @classmethod
    def discover(cls, path, depth="0"):
        """Discover a list of collections under the given ``path``.

        If ``depth`` is "0", only the actual object under ``path`` is
        returned.

        If ``depth`` is anything but "0", it is considered as "1" and direct
        children are included in the result.

        The ``path`` is relative.

        The root collection "/" must always exist.

        """

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
                collection = cls(path, _is_principal(path))
                yield collection.get(item)
                return

            collection = cls(path, _is_principal(path))
        except api.exceptions.DoesNotExist:
            return

        yield collection

        if depth == "0":
            return

        if len(attributes) == 0:
            yield cls(posixpath.join(path, cls.user), principal=True)
        elif len(attributes) == 1:
            for journal in cls.etesync.list():
                if journal.collection.TYPE in (api.AddressBook.TYPE, api.Calendar.TYPE, api.TaskList.TYPE):
                    yield cls(posixpath.join(path, journal.uid), principal=False)
        elif len(attributes) == 2:
            for item in collection.list():
                yield collection.get(item)

        elif len(attributes) > 2:
            raise RuntimeError("Found more than one attribute. Shouldn't happen")

    @property
    def etag(self):
        """Encoded as quoted-string (see RFC 2616)."""
        if self.is_fake:
            return

        entry = None
        for entry in self.journal.list():
            pass

        return entry.uid if entry is not None else hashlib.sha256(b"").hexdigest()

    @staticmethod
    def _find_available_file_name(exists_fn, suffix=""):
        # Prevent infinite loop
        for _ in range(1000):
            file_name = str(uuid4()) + suffix
            if not exists_fn(file_name):
                return file_name
        # something is wrong with the PRNG
        raise RuntimeError("No unique random sequence found")

    @classmethod
    def create_collection(cls, href, collection=None, props=None):
        """Create a collection.

        If the collection already exists and neither ``collection`` nor
        ``props`` are set, this method shouldn't do anything. Otherwise the
        existing collection must be replaced.

        ``collection`` is a list of vobject components.

        ``props`` are metadata values for the collection.

        ``props["tag"]`` is the type of collection (VCALENDAR or
        VADDRESSBOOK). If the key ``tag`` is missing, it is guessed from the
        collection.

        """
        # Path should already be sanitized
        attributes = _get_attributes_from_path(href)
        if len(attributes) <= 1:
            raise PrincipalNotAllowedError

        # Try to infer tag
        if not props:
            props = {}
        if not props.get("tag") and collection:
            props["tag"] = collection[0].name

        # Try first getting the collection if exists, or create a new one otherwise.
        try:
            self = cls(href, principal=False, tag=props.get("tag"))
        except api.exceptions.DoesNotExist:
            user_path = posixpath.join('/', cls.user)
            collection_name = hashlib.sha256(str(time.time()).encode()).hexdigest()
            sane_path = posixpath.join(user_path, collection_name)

            if props.get("tag") == "VCALENDAR":
                inst = api.Calendar.create(cls.etesync, collection_name, None)
            elif props.get("tag") == "VADDRESSBOOK":
                inst = api.AddressBook.create(cls.etesync, collection_name, None)
            else:
                raise RuntimeError("Bad tag.")

            inst.save()
            self = cls(sane_path, principal=False)

        self.set_meta(props)

        if collection:
            if props.get("tag") == "VCALENDAR":
                collection, = collection
                items = []
                for content in ("vevent", "vtodo", "vjournal"):
                    items.extend(
                        getattr(collection, "%s_list" % content, []))
                items_by_uid = groupby(sorted(items, key=get_uid), get_uid)
                vobject_items = {}
                for uid, items in items_by_uid:
                    new_collection = vobject.iCalendar()
                    for item in items:
                        new_collection.add(item)
                    href = self._find_available_file_name(
                        vobject_items.get)
                    vobject_items[href] = new_collection
                self._upload_all_nonatomic(vobject_items)
            elif props.get("tag") == "VADDRESSBOOK":
                vobject_items = {}
                for card in collection:
                    href = self._find_available_file_name(
                        vobject_items.get)
                    vobject_items[href] = card
                self._upload_all_nonatomic(vobject_items)

        return self

    def sync(self, old_token=None):
        """Get the current sync token and changed items for synchronization.

        ``old_token`` an old sync token which is used as the base of the
        delta update. If sync token is missing, all items are returned.
        ValueError is raised for invalid or old tokens.
        """
        # FIXME: Actually implement
        token = "http://radicale.org/ns/sync/%s" % self.etag.strip("\"")
        if old_token:
            raise ValueError("Sync token are not supported (you can ignore this warning)")
        return token, self.list()

    def list(self):
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

    def get(self, href):
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
            # XXX Hack to remove photo until we fix its handling
            if 'photo' in item.contents:
                del item.contents['photo']
        except Exception as e:
            raise RuntimeError("Failed to parse item %r in %r" %
                               (href, self.path)) from e
        # FIXME: Make this sensible
        last_modified = time.strftime(
            "%a, %d %b %Y %H:%M:%S GMT",
            time.gmtime(time.time()))
        return EteSyncItem(self, item, href, last_modified=last_modified, etesync_item=etesync_item)

    def _upload_all_nonatomic(self, items):
        for href in items:
            self.upload(href, items[href])

    def upload(self, href, vobject_item):
        """Upload a new or replace an existing item."""
        if self.is_fake:
            return

        content = vobject_item.serialize()

        item = self.get(href)
        if item is not None:
            etesync_item = item.etesync_item
            etesync_item.content = content
            etesync_item.save()
        else:
            etesync_item = self.collection.get_content_class().create(self.collection, content)
            etesync_item.save()
            href_mapper = HrefMapper(content=etesync_item._cache_obj, href=href)
            href_mapper.save(force_insert=True)

        return self.get(href)

    def delete(self, href=None):
        """Delete an item.

        When ``href`` is ``None``, delete the collection.

        """
        if self.is_fake:
            return

        if href is None:
            self.collection.delete()
            return

        item = self.get(href)
        if item is None:
            raise ComponentNotFoundError(href)

        item.etesync_item.delete()

    def get_meta(self, key=None):
        """Get metadata value for collection."""
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
        """Set metadata values for collection."""
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

    # FIXME: Copied from Radicale because of their bug
    def set_meta_all(self, props):
        """Set metadata values for collection.

        ``props`` a dict with values for properties.

        """
        delta_props = self.get_meta()
        for key in delta_props.keys():
            if key not in props:
                delta_props[key] = None
        delta_props.update(props)
        self.set_meta(delta_props)

    @property
    def last_modified(self):
        """Get the HTTP-datetime of when the collection was modified."""
        # FIXME: Make this sensible
        last_modified = time.strftime(
            "%a, %d %b %Y %H:%M:%S GMT",
            time.gmtime(time.time()))
        return last_modified

    def serialize(self):
        """Get the unicode string representing the whole collection."""
        import datetime
        items = []
        time_begin = datetime.datetime.now()
        for href in self.list():
            items.append(self.get(href).item)
        time_end = datetime.datetime.now()
        self.logger.info(
            "Collection read %d items in %s sec from %s", len(items),
            (time_end - time_begin).total_seconds(), self.path)
        if self.get_meta("tag") == "VCALENDAR":
            collection = vobject.iCalendar()
            for item in items:
                for content in ("vevent", "vtodo", "vjournal"):
                    if content in item.contents:
                        for item_part in getattr(item, "%s_list" % content):
                            collection.add(item_part)
                        break
            return collection.serialize()
        elif self.get_meta("tag") == "VADDRESSBOOK":
            return "".join([item.serialize() for item in items])
        return ""

    @classmethod
    def _should_sync(cls):
        return time.time() - cls.etesync.last_sync >= 2 * 60  # In seconds

    @classmethod
    def _mark_sync(cls):
        cls.etesync.last_sync = time.time()

    @classmethod
    def _get_etesync_for_user(cls, user):
        if cls._etesync_cache is None:
            cls._etesync_cache = EteSyncCache(
                creds_path=cls.configuration.get(CONFIG_SECTION, "credentials_filename"),
                db_path=cls.configuration.get(CONFIG_SECTION, "database_filename"),
                remote_url=cls.configuration.get(CONFIG_SECTION, "remote_url"),
            )

        etesync, created = cls._etesync_cache.etesync_for_user(user)

        if created:
            etesync.last_sync = 0

        return etesync

    @classmethod
    @contextmanager
    def acquire_lock(cls, mode, user=None):
        """Set a context manager to lock the whole storage.

        ``mode`` must either be "r" for shared access or "w" for exclusive
        access.

        ``user`` is the name of the logged in user or empty.

        """
        if not user:
            return

        with EteSyncCache.lock:
            cls.user = user

            cls.etesync = cls._get_etesync_for_user(cls.user)

            if cls._should_sync():
                cls._mark_sync()
                cls.etesync.get_or_create_user_info(force_fetch=True)
                cls.etesync.sync_journal_list()
                for journal in cls.etesync.list():
                    cls.etesync.pull_journal(journal.uid)
            yield
            if cls.etesync.journal_list_is_dirty():
                cls.etesync.sync_journal_list()
            for journal in cls.etesync.list():
                if cls.etesync.journal_is_dirty(journal.uid):
                    cls.etesync.sync_journal(journal.uid)

            cls.etesync = None
            cls.user = None
