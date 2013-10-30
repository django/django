from django.db.backends.oracle.base import DatabaseWrapper as OracleDatabaseWrapper
from django.contrib.gis.db.backends.oracle.creation import OracleCreation
from django.contrib.gis.db.backends.oracle.introspection import OracleIntrospection
from django.contrib.gis.db.backends.oracle.operations import OracleOperations


class DatabaseWrapper(OracleDatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.ops = OracleOperations(self)
        self.creation = OracleCreation(self)
        self.introspection = OracleIntrospection(self)
