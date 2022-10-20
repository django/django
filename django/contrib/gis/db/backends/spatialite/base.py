from ctypes.util import find_library

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper

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
        self.lib_spatialite_paths = [
            name
            for name in [
                getattr(settings, "SPATIALITE_LIBRARY_PATH", None),
                "mod_spatialite.so",
                "mod_spatialite",
                find_library("spatialite"),
            ]
            if name is not None
        ]
        super().__init__(*args, **kwargs)

    def get_new_connection(self, conn_params):
        conn = super().get_new_connection(conn_params)
        # Enabling extension loading on the SQLite connection.
        try:
            conn.enable_load_extension(True)
        except AttributeError:
            raise ImproperlyConfigured(
                "SpatiaLite requires SQLite to be configured to allow "
                "extension loading."
            )
        # Load the SpatiaLite library extension on the connection.
        for path in self.lib_spatialite_paths:
            try:
                conn.load_extension(path)
            except Exception:
                if getattr(settings, "SPATIALITE_LIBRARY_PATH", None):
                    raise ImproperlyConfigured(
                        "Unable to load the SpatiaLite library extension "
                        "as specified in your SPATIALITE_LIBRARY_PATH setting."
                    )
                continue
            else:
                break
        else:
            raise ImproperlyConfigured(
                "Unable to load the SpatiaLite library extension. "
                "Library names tried: %s" % ", ".join(self.lib_spatialite_paths)
            )
        return conn

    def prepare_database(self):
        super().prepare_database()
        # Check if spatial metadata have been initialized in the database
        with self.cursor() as cursor:
            cursor.execute("PRAGMA table_info(geometry_columns);")
            if cursor.fetchall() == []:
                if self.ops.spatial_version < (5,):
                    cursor.execute("SELECT InitSpatialMetaData(1)")
                else:
                    cursor.execute("SELECT InitSpatialMetaDataFull(1)")
