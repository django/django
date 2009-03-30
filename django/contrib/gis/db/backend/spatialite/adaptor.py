from django.db.backends.sqlite3.base import Database
from django.contrib.gis.db.backend.adaptor import WKTAdaptor

class SpatiaLiteAdaptor(WKTAdaptor):
    "SQLite adaptor for geometry objects."
    def __conform__(self, protocol):
        if protocol is Database.PrepareProtocol:
            return str(self)
