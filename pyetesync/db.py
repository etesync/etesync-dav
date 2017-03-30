import peewee as pw
from playhouse.sqlite_ext import SqliteExtDatabase

db = SqliteExtDatabase('etesync.db')
db.connect()


class BaseModel(pw.Model):
    class Meta:
        database = db
