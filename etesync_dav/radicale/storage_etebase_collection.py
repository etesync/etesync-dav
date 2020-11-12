import re

from radicale import pathutils
from radicale.item import Item
from radicale.storage import (
        BaseCollection, ComponentNotFoundError,
    )
import vobject

from ..local_cache.models import HrefMapper


class MetaMapping:
    # Mappings between etesync meta and radicale
    _mappings = {
            "D:displayname": ("name", None, None),
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


class MetaMappingCalendar(MetaMapping):
    supported_calendar_component = 'VEVENT'
    _mappings = MetaMapping._mappings.copy()
    _mappings.update({
            "C:calendar-description": ("description", None, None),
            "ICAL:calendar-color": ("color", None, None),
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
        return '"{}"'.format(self.etesync_item.etag)


class Collection(BaseCollection):
    def __init__(self, storage_, path):
        self._storage = storage_
        # Path should already be sanitized
        self._path = pathutils.sanitize_path(path).strip("/")

        attributes = _get_attributes_from_path(path)
        self.etesync = self._storage.etesync
        if len(attributes) == 2:
            self.uid = attributes[-1]
            self.collection = self.etesync.get(self.uid)
            col_type = self.collection.col_type
            if col_type == "etebase.vevent":
                self.tag = "VCALENDAR"
                self.meta_mappings = MetaMappingCalendar()
                self.content_suffix = ".ics"
            elif col_type == "etebase.vtodo":
                self.tag = "VCALENDAR"
                self.meta_mappings = MetaMappingTaskList()
                self.content_suffix = ".ics"
            elif col_type == "etebase.vcard":
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

        return '"{}"'.format(self.collection.stoken)

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
                href_mapper = item.cache_item.href.get()
            except HrefMapper.DoesNotExist:
                # Generate a new mapper
                href = item.item.uid + self.content_suffix
                href_mapper = HrefMapper(content=item.cache_item, href=href)
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

        if etesync_item is None:
            return None

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

        item = self._get(href)
        if item is not None:
            etesync_item = item.etesync_item
            etesync_item.content = vobject_item.serialize()
            etesync_item.save()
        else:
            etesync_item = self.collection.create(vobject_item)
            etesync_item.save()
            href_mapper = HrefMapper(content=etesync_item.cache_item, href=href)
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
            meta = self.collection.meta
            for key in meta.keys():
                ret[key] = self.meta_mappings.map_get(meta, key)[1]
            return ret
        else:
            meta = self.collection.meta
            key, value = self.meta_mappings.map_get(meta, key)
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

        self.collection.update_meta(props)
        self.collection.save()

    @property
    def last_modified(self):
        """Get the HTTP-datetime of when the collection was modified."""
        return ''
