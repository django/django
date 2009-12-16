from django.db.backends.oracle.base import *
from django.db.backends.oracle.base import DatabaseWrapper as OracleDatabaseWrapper
from django.contrib.gis.db.backends.oracle.creation import OracleCreation
from django.contrib.gis.db.backends.oracle.operations import OracleOperations

class DatabaseWrapper(OracleDatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.creation = OracleCreation(self)
        self.ops = OracleOperations(self)
