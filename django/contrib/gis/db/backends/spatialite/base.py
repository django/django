from ctypes.util import find_library

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.sqlite3.base import (
    DatabaseWrapper as SQLiteDatabaseWrapper, SQLiteCursorWrapper,
)

from .client import SpatiaLiteClient
from .features import DatabaseFeatures
from .introspection import SpatiaLiteIntrospection
from .operations import SpatiaLiteOperations
from .schema import SpatialiteSchemaEditor


class DatabaseWrapper(SQLiteDatabaseWrapper):
    SchemaEditorClass = SpatialiteSchemaEditor
    # Classes instantiated in __init__().
    client_class = SpatiaLiteClient
    features_class = DatabaseFeatures
    introspection_class = SpatiaLiteIntrospection
    ops_class = SpatiaLiteOperations

    def __init__(self, *args, **kwargs):
        # Trying to find the location of the SpatiaLite library.
        # Here we are figuring out the path to the SpatiaLite library
        # (`libspatialite`). If it's not in the system library path (e.g., it
        # cannot be found by `ctypes.util.find_library`), then it may be set
        # manually in the settings via the `SPATIALITE_LIBRARY_PATH` setting.
        self.spatialite_lib = getattr(settings, 'SPATIALITE_LIBRARY_PATH',
                                      find_library('spatialite'))
        if not self.spatialite_lib:
            raise ImproperlyConfigured('Unable to locate the SpatiaLite library. '
                                       'Make sure it is in your library path, or set '
                                       'SPATIALITE_LIBRARY_PATH in your settings.'
                                       )
        super().__init__(*args, **kwargs)

    def get_new_connection(self, conn_params):
        conn = super().get_new_connection(conn_params)
        # Enabling extension loading on the SQLite connection.
        try:
            conn.enable_load_extension(True)
        except AttributeError:
            raise ImproperlyConfigured(
                'SpatiaLite requires SQLite to be configured to allow '
                'extension loading.'
            )
        # Loading the SpatiaLite library extension on the connection, and returning
        # the created cursor.
        cur = conn.cursor(factory=SQLiteCursorWrapper)
        try:
            cur.execute("SELECT load_extension(%s)", (self.spatialite_lib,))
        except Exception as exc:
            raise ImproperlyConfigured(
                'Unable to load the SpatiaLite library extension "%s"' % self.spatialite_lib
            ) from exc
        cur.close()
        return conn

    def prepare_database(self):
        super().prepare_database()
        # Check if spatial metadata have been initialized in the database
        with self.cursor() as cursor:
            cursor.execute("PRAGMA table_info(geometry_columns);")
            if cursor.fetchall() == []:
                arg = "1" if self.features.supports_initspatialmetadata_in_one_transaction else ""
                cursor.execute("SELECT InitSpatialMetaData(%s)" % arg)
