import peewee as pw

from . import db


class User(db.BaseModel):
    username = pw.CharField(unique=True, null=False)


class JournalEntity(db.BaseModel):
    local_user = pw.ForeignKeyField(User, related_name='journals')
    version = pw.IntegerField()
    uid = pw.CharField(null=False, index=True)
    owner = pw.CharField(null=True)
    encrypted_key = pw.TextField(null=True)
    content = pw.TextField()
    new = pw.BooleanField(null=False, default=False)
    dirty = pw.BooleanField(null=False, default=False)
    deleted = pw.BooleanField(null=False, default=False)

    class Meta:
        indexes = (
            (('local_user', 'uid'), True),
        )


class EntryEntity(db.BaseModel):
    journal = pw.ForeignKeyField(JournalEntity, related_name='entries')
    uid = pw.CharField(null=False, index=True)
    content = pw.TextField()
    new = pw.BooleanField(null=False, default=False)

    class Meta:
        indexes = (
            (('journal', 'uid'), True),
        )
        order_by = ('id', )


class UserInfo(db.BaseModel):
    user = pw.ForeignKeyField(User, primary_key=True, related_name='user_info')
    pubkey = pw.TextField(null=False)
    content = pw.TextField(null=False)
