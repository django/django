from django.db.backends.oracle.base import (
    DatabaseWrapper as OracleDatabaseWrapper,
    DatabaseFeatures as OracleDatabaseFeatures,
)
from django.contrib.gis.db.backends.base import BaseSpatialFeatures
from django.contrib.gis.db.backends.oracle.creation import OracleCreation
from django.contrib.gis.db.backends.oracle.introspection import OracleIntrospection
from django.contrib.gis.db.backends.oracle.operations import OracleOperations
from django.contrib.gis.db.backends.oracle.schema import OracleGISSchemaEditor


class DatabaseFeatures(BaseSpatialFeatures, OracleDatabaseFeatures):
    supports_add_srs_entry = False
    supports_geometry_field_introspection = False


class DatabaseWrapper(OracleDatabaseWrapper):
    SchemaEditorClass = OracleGISSchemaEditor

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.features = DatabaseFeatures(self)
        self.ops = OracleOperations(self)
        self.creation = OracleCreation(self)
        self.introspection = OracleIntrospection(self)
