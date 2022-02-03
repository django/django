from django.db.backends.oracle.base import DatabaseWrapper as OracleDatabaseWrapper

from .features import DatabaseFeatures
from .introspection import OracleIntrospection
from .operations import OracleOperations
from .schema import OracleGISSchemaEditor


class DatabaseWrapper(OracleDatabaseWrapper):
    SchemaEditorClass = OracleGISSchemaEditor
    # Classes instantiated in __init__().
    features_class = DatabaseFeatures
    introspection_class = OracleIntrospection
    ops_class = OracleOperations
