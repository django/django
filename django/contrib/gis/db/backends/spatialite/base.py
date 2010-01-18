from ctypes.util import find_library
from django.conf import settings

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.sqlite3.base import *
from django.db.backends.sqlite3.base import DatabaseWrapper as SqliteDatabaseWrapper, \
    _sqlite_extract, _sqlite_date_trunc, _sqlite_regexp
from django.contrib.gis.db.backends.spatialite.client import SpatiaLiteClient
from django.contrib.gis.db.backends.spatialite.creation import SpatiaLiteCreation
from django.contrib.gis.db.backends.spatialite.introspection import SpatiaLiteIntrospection
from django.contrib.gis.db.backends.spatialite.operations import SpatiaLiteOperations

class DatabaseWrapper(SqliteDatabaseWrapper):
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
        self.ops = SpatiaLiteOperations(self)
        self.client = SpatiaLiteClient(self)
        self.creation = SpatiaLiteCreation(self)
        self.introspection = SpatiaLiteIntrospection(self)

    def _cursor(self):
        if self.connection is None:
            ## The following is the same as in django.db.backends.sqlite3.base ##
            settings_dict = self.settings_dict
            if not settings_dict['NAME']:
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("Please fill out the database NAME in the settings module before using the database.")
            kwargs = {
                'database': settings_dict['NAME'],
                'detect_types': Database.PARSE_DECLTYPES | Database.PARSE_COLNAMES,
            }
            kwargs.update(settings_dict['OPTIONS'])
            self.connection = Database.connect(**kwargs)
            # Register extract, date_trunc, and regexp functions.
            self.connection.create_function("django_extract", 2, _sqlite_extract)
            self.connection.create_function("django_date_trunc", 2, _sqlite_date_trunc)
            self.connection.create_function("regexp", 2, _sqlite_regexp)
            connection_created.send(sender=self.__class__)

            ## From here on, customized for GeoDjango ##

            # Enabling extension loading on the SQLite connection.
            try:
                self.connection.enable_load_extension(True)
            except AttributeError:
                raise ImproperlyConfigured('The pysqlite library does not support C extension loading. '
                                           'Both SQLite and pysqlite must be configured to allow '
                                           'the loading of extensions to use SpatiaLite.'
                                           )

            # Loading the SpatiaLite library extension on the connection, and returning
            # the created cursor.
            cur = self.connection.cursor(factory=SQLiteCursorWrapper)
            try:
                cur.execute("SELECT load_extension(%s)", (self.spatialite_lib,))
            except Exception, msg:
                raise ImproperlyConfigured('Unable to load the SpatiaLite library extension '
                                           '"%s" because: %s' % (self.spatialite_lib, msg))
            return cur
        else:
            return self.connection.cursor(factory=SQLiteCursorWrapper)
