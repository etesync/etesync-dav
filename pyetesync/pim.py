import peewee as pw
import vobject

from .cache import JournalEntity
from . import db


class BaseContent(db.BaseModel):
    journal = pw.ForeignKeyField(JournalEntity)
    uid = pw.UUIDField(null=False, index=True)
    content = pw.BlobField()
    dirty = pw.BooleanField(null=False, default=False)
    deleted = pw.BooleanField(null=False, default=False)

    class Meta:
        indexes = (
            (('journal', 'uid'), True),
        )

    @classmethod
    def apply_sync_entry(cls, journal, sync_entry):
        uid = cls.get_uid(sync_entry)

        try:
            content = cls.get(uid=uid, journal=journal)
        except cls.DoesNotExist:
            content = None

        if sync_entry.action == 'DELETE':
            if content is not None:
                content.delete_instance()
            else:
                print("WARNING: Failed to delete " + uid)

            return

        content = cls(journal=journal, uid=uid) if content is None else content

        content.content = sync_entry.content
        content.save()


class Event(BaseContent):
    @classmethod
    def get_uid(cls, sync_entry):
        vobj = vobject.readOne(sync_entry.content)
        return vobj.vevent.uid.value


class Contact(BaseContent):
    @classmethod
    def get_uid(cls, sync_entry):
        vobj = vobject.readOne(sync_entry.content)
        return vobj.uid.value


db.db.create_tables([Event, Contact], safe=True)
