import sys
from ctypes.util import find_library

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.sqlite3.base import (
    Database, DatabaseWrapper as SQLiteDatabaseWrapper, SQLiteCursorWrapper,
)
from django.utils import six

from .client import SpatiaLiteClient
from .features import DatabaseFeatures
from .introspection import SpatiaLiteIntrospection
from .operations import SpatiaLiteOperations
from .schema import SpatialiteSchemaEditor


class DatabaseWrapper(SQLiteDatabaseWrapper):
    SchemaEditorClass = SpatialiteSchemaEditor

    def __init__(self, *args, **kwargs):
        # Before we get too far, make sure pysqlite 2.5+ is installed.
        if Database.version_info < (2, 5, 0):
            raise ImproperlyConfigured('Only versions of pysqlite 2.5+ are '
                                       'compatible with SpatiaLite and GeoDjango.')

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
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.features = DatabaseFeatures(self)
        self.ops = SpatiaLiteOperations(self)
        self.client = SpatiaLiteClient(self)
        self.introspection = SpatiaLiteIntrospection(self)

    def get_new_connection(self, conn_params):
        conn = super(DatabaseWrapper, self).get_new_connection(conn_params)
        # Enabling extension loading on the SQLite connection.
        try:
            conn.enable_load_extension(True)
        except AttributeError:
            raise ImproperlyConfigured(
                'The pysqlite library does not support C extension loading. '
                'Both SQLite and pysqlite must be configured to allow '
                'the loading of extensions to use SpatiaLite.')
        # Loading the SpatiaLite library extension on the connection, and returning
        # the created cursor.
        cur = conn.cursor(factory=SQLiteCursorWrapper)
        try:
            cur.execute("SELECT load_extension(%s)", (self.spatialite_lib,))
        except Exception as msg:
            new_msg = (
                'Unable to load the SpatiaLite library extension '
                '"%s" because: %s') % (self.spatialite_lib, msg)
            six.reraise(ImproperlyConfigured, ImproperlyConfigured(new_msg), sys.exc_info()[2])
        cur.close()
        return conn

    def prepare_database(self):
        super(DatabaseWrapper, self).prepare_database()
        # Check if spatial metadata have been initialized in the database
        with self.cursor() as cursor:
            cursor.execute("PRAGMA table_info(geometry_columns);")
            if cursor.fetchall() == []:
                arg = "1" if self.features.supports_initspatialmetadata_in_one_transaction else ""
                cursor.execute("SELECT InitSpatialMetaData(%s)" % arg)
