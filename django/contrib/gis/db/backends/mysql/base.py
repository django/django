from django.db.backends.mysql.base import (
    DatabaseWrapper as MySQLDatabaseWrapper,
)

from .features import DatabaseFeatures
from .introspection import MySQLIntrospection
from .operations import MySQLOperations
from .schema import MySQLGISSchemaEditor


class DatabaseWrapper(MySQLDatabaseWrapper):
    SchemaEditorClass = MySQLGISSchemaEditor
    # Classes instantiated in __init__().
    features_class = DatabaseFeatures
    introspection_class = MySQLIntrospection
    ops_class = MySQLOperations
