import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db.backends.sqlite3.creation import DatabaseCreation

class SpatiaLiteCreation(DatabaseCreation):

    def create_test_db(self, verbosity=1, autoclobber=False):
        """
        Creates a test database, prompting the user for confirmation if the
        database already exists. Returns the name of the test database created.

        This method is overloaded to load up the SpatiaLite initialization
        SQL prior to calling the `syncdb` command.
        """
        if verbosity >= 1:
            print "Creating test database '%s'..." % self.connection.alias

        test_database_name = self._create_test_db(verbosity, autoclobber)

        self.connection.close()

        self.connection.settings_dict["NAME"] = test_database_name
        can_rollback = self._rollback_works()
        self.connection.settings_dict["SUPPORTS_TRANSACTIONS"] = can_rollback
        # Need to load the SpatiaLite initialization SQL before running `syncdb`.
        self.load_spatialite_sql()
        call_command('syncdb', verbosity=verbosity, interactive=False, database=self.connection.alias)

        if settings.CACHE_BACKEND.startswith('db://'):
            from django.core.cache import parse_backend_uri
            _, cache_name, _ = parse_backend_uri(settings.CACHE_BACKEND)
            call_command('createcachetable', cache_name)

        # Get a cursor (even though we don't need one yet). This has
        # the side effect of initializing the test database.
        cursor = self.connection.cursor()

        return test_database_name

    def sql_indexes_for_field(self, model, f, style):
        "Return any spatial index creation SQL for the field."
        from django.contrib.gis.db.models.fields import GeometryField

        output = super(SpatiaLiteCreation, self).sql_indexes_for_field(model, f, style)

        if isinstance(f, GeometryField):
            gqn = self.connection.ops.geo_quote_name
            qn = self.connection.ops.quote_name
            db_table = model._meta.db_table

            output.append(style.SQL_KEYWORD('SELECT ') +
                          style.SQL_TABLE('AddGeometryColumn') + '(' +
                          style.SQL_TABLE(gqn(db_table)) + ', ' +
                          style.SQL_FIELD(gqn(f.column)) + ', ' +
                          style.SQL_FIELD(str(f.srid)) + ', ' +
                          style.SQL_COLTYPE(gqn(f.geom_type)) + ', ' +
                          style.SQL_KEYWORD(str(f.dim)) + ', ' +
                          style.SQL_KEYWORD(str(int(not f.null))) +
                          ');')

            if f.spatial_index:
                output.append(style.SQL_KEYWORD('SELECT ') +
                              style.SQL_TABLE('CreateSpatialIndex') + '(' +
                              style.SQL_TABLE(gqn(db_table)) + ', ' +
                              style.SQL_FIELD(gqn(f.column)) + ');')

        return output

    def load_spatialite_sql(self):
        """
        This routine loads up the SpatiaLite SQL file.
        """
        # Getting the location of the SpatiaLite SQL file, and confirming
        # it exists.
        spatialite_sql = self.spatialite_init_file()
        if not os.path.isfile(spatialite_sql):
            raise ImproperlyConfigured('Could not find the required SpatiaLite initialization '
                                       'SQL file (necessary for testing): %s' % spatialite_sql)

        # Opening up the SpatiaLite SQL initialization file and executing
        # as a script.
        sql_fh = open(spatialite_sql, 'r')
        try:
            cur = self.connection._cursor()
            cur.executescript(sql_fh.read())
        finally:
            sql_fh.close()

    def spatialite_init_file(self):
        # SPATIALITE_SQL may be placed in settings to tell GeoDjango
        # to use a specific path to the SpatiaLite initilization SQL.
        return getattr(settings, 'SPATIALITE_SQL',
                       'init_spatialite-%s.%s.sql' %
                       self.connection.ops.spatial_version[:2])
