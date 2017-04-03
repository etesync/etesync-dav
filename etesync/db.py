import peewee as pw

database_proxy = pw.Proxy()


class BaseModel(pw.Model):
    class Meta:
        database = database_proxy
