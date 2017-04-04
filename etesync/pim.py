import peewee as pw

from .cache import JournalEntity
from . import db


class Content(db.BaseModel):
    journal = pw.ForeignKeyField(JournalEntity)
    uid = pw.CharField(null=False, index=True)
    content = pw.TextField()
    new = pw.BooleanField(null=False, default=False)
    dirty = pw.BooleanField(null=False, default=False)
    deleted = pw.BooleanField(null=False, default=False)

    class Meta:
        indexes = (
            (('journal', 'uid'), True),
        )
