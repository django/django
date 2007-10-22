from types import StringType, UnicodeType
from django.db import connection
from django.db.models.fields import Field # Django base Field class
from django.contrib.gis.geos import GEOSGeometry, GEOSException 
from django.contrib.gis.db.backend.util import get_srid, GeoFieldSQL
from django.contrib.gis.db.backend.postgis.adaptor import PostGISAdaptor
from django.contrib.gis.db.backend.postgis.query import POSTGIS_TERMS, TRANSFORM
from psycopg2 import Binary

# Quotename & geographic quotename, respectively
qn = connection.ops.quote_name
def gqn(value):
    if isinstance(value, UnicodeType): value = value.encode('ascii')
    return "'%s'" % value

class PostGISField(Field):
    def _add_geom(self, style, db_table):
        """
        Constructs the addition of the geometry to the table using the
        AddGeometryColumn(...) PostGIS (and OGC standard) stored procedure.

        Takes the style object (provides syntax highlighting) and the
        database table as parameters.
        """
        sql = style.SQL_KEYWORD('SELECT ') + \
              style.SQL_TABLE('AddGeometryColumn') + '(' + \
              style.SQL_TABLE(gqn(db_table)) + ', ' + \
              style.SQL_FIELD(gqn(self.column)) + ', ' + \
              style.SQL_FIELD(str(self._srid)) + ', ' + \
              style.SQL_COLTYPE(gqn(self._geom)) + ', ' + \
              style.SQL_KEYWORD(str(self._dim)) + ');'

        if not self.null:
            # Add a NOT NULL constraint to the field
            sql += '\n' + \
                   style.SQL_KEYWORD('ALTER TABLE ') + \
                   style.SQL_TABLE(qn(db_table)) + \
                   style.SQL_KEYWORD(' ALTER ') + \
                   style.SQL_FIELD(qn(self.column)) + \
                   style.SQL_KEYWORD(' SET NOT NULL') + ';'
        return sql
    
    def _geom_index(self, style, db_table,
                    index_type='GIST', index_opts='GIST_GEOMETRY_OPS'):
        "Creates a GiST index for this geometry field."
        sql = style.SQL_KEYWORD('CREATE INDEX ') + \
              style.SQL_TABLE(qn('%s_%s_id' % (db_table, self.column))) + \
              style.SQL_KEYWORD(' ON ') + \
              style.SQL_TABLE(qn(db_table)) + \
              style.SQL_KEYWORD(' USING ') + \
              style.SQL_COLTYPE(index_type) + ' ( ' + \
              style.SQL_FIELD(qn(self.column)) + ' ' + \
              style.SQL_KEYWORD(index_opts) + ' );'
        return sql

    def _post_create_sql(self, style, db_table):
        """
        Returns SQL that will be executed after the model has been
        created. Geometry columns must be added after creation with the
        PostGIS AddGeometryColumn() function.
        """

        # Getting the AddGeometryColumn() SQL necessary to create a PostGIS
        # geometry field.
        post_sql = self._add_geom(style, db_table)

        # If the user wants to index this data, then get the indexing SQL as well.
        if self._index:
            return (post_sql, self._geom_index(style, db_table))
        else:
            return (post_sql,)

    def _post_delete_sql(self, style, db_table):
        "Drops the geometry column."
        sql = style.SQL_KEYWORD('SELECT ') + \
            style.SQL_KEYWORD('DropGeometryColumn') + '(' + \
            style.SQL_TABLE(gqn(db_table)) + ', ' + \
            style.SQL_FIELD(gqn(self.column)) +  ');'
        return sql

    def db_type(self):
        """
        PostGIS geometry columns are added by stored procedures, should be
        None.
        """
        return None

    def get_db_prep_lookup(self, lookup_type, value):
        """
        Returns field's value prepared for database lookup, accepts WKT and 
        GEOS Geometries for the value.
        """
        if lookup_type in POSTGIS_TERMS:
            # special case for isnull lookup
            if lookup_type == 'isnull':
                return GeoFieldSQL([], [value])

            # When the input is not a GEOS geometry, attempt to construct one
            # from the given string input.
            if isinstance(value, GEOSGeometry):
                pass
            elif isinstance(value, (StringType, UnicodeType)):
                try:
                    value = GEOSGeometry(value)
                except GEOSException:
                    raise TypeError("Could not create geometry from lookup value: %s" % str(value))
            else:
                raise TypeError('Cannot use parameter of %s type as lookup parameter.' % type(value))

            # Getting the SRID of the geometry, or defaulting to that of the field if
            # it is None.
            srid = get_srid(self, value)

            # The adaptor will be used by psycopg2 for quoting the WKB.
            adapt = PostGISAdaptor(value, srid)

            if srid != self._srid:
                # Adding the necessary string substitutions and parameters
                # to perform a geometry transformation.
                return GeoFieldSQL(['%s(%%s,%%s)' % TRANSFORM],
                                   [adapt, self._srid])
            else:
                return GeoFieldSQL(['%s'], [adapt])
        else:
            raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def get_db_prep_save(self, value):
        "Prepares the value for saving in the database."
        if not bool(value): return None
        if isinstance(value, GEOSGeometry):
            return PostGISAdaptor(value, value.srid)
        else:
            raise TypeError('Geometry Proxy should only return GEOSGeometry objects.')

    def get_internal_type(self):
        """
        Returns NoField because a stored procedure is used by PostGIS to create
        the Geometry Fields.
        """
        return 'NoField'

    def get_placeholder(self, value):
        """
        Provides a proper substitution value for Geometries that are not in the
        SRID of the field.  Specifically, this routine will substitute in the
        ST_Transform() function call.
        """
        if isinstance(value, GEOSGeometry) and value.srid != self._srid:
            # Adding Transform() to the SQL placeholder.
            return '%s(%%s, %s)' % (TRANSFORM, self._srid)
        else:
            return '%s'
