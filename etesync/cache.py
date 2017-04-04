import peewee as pw

from . import db


class User(db.BaseModel):
    username = pw.CharField(unique=True, null=False)


class JournalEntity(db.BaseModel):
    owner = pw.ForeignKeyField(User, related_name='journals')
    version = pw.IntegerField()
    uid = pw.CharField(unique=True, null=False, index=True)
    content = pw.TextField()
    new = pw.BooleanField(null=False, default=False)
    dirty = pw.BooleanField(null=False, default=False)
    deleted = pw.BooleanField(null=False, default=False)


class EntryEntity(db.BaseModel):
    journal = pw.ForeignKeyField(JournalEntity, related_name='entries')
    uid = pw.CharField(unique=True, null=False, index=True)
    content = pw.TextField()
    new = pw.BooleanField(null=False, default=False)

    class Meta:
        order_by = ('id', )
