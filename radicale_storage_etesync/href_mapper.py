import peewee as pw

import etesync as api


class HrefMapper(api.db.BaseModel):
    content = pw.ForeignKeyField(api.pim.Content, primary_key=True, backref='href', on_delete='CASCADE')
    href = pw.CharField(null=False, index=True)
