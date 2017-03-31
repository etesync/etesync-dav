import os

import peewee as pw
from playhouse.sqlite_ext import SqliteExtDatabase

directory = os.path.join(os.path.expanduser('~'), '.pyetesync')

if not os.path.exists(directory):
    os.makedirs(directory)

db = SqliteExtDatabase(os.path.join(directory, 'data.db'))
db.connect()


class BaseModel(pw.Model):
    class Meta:
        database = db
