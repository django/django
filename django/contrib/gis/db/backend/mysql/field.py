import re
from types import StringType, UnicodeType
from django.db import connection
from django.db.models.fields import Field # Django base Field class
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.backend.util import GeoFieldSQL
from django.contrib.gis.db.backend.mysql.query import MYSQL_GIS_TERMS, GEOM_FROM_TEXT

# Quotename & geographic quotename, respectively.
qn = connection.ops.quote_name
def gqn(value):
    if isinstance(value, UnicodeType): value = value.encode('ascii')
    return "'%s'" % value

class MySQLGeoField(Field):
    """
    The backend-specific geographic field for MySQL.
    """

    def _geom_index(self, style, db_table):
        """
        Creates a spatial index for the geometry column.  If MyISAM tables are
        used an R-Tree index is created, otherwise a B-Tree index is created. 
        Thus, for best spatial performance, you should use MyISAM tables
        (which do not support transactions).  For more information, see Ch. 
        17.6.1 of the MySQL 5.0 documentation.
        """

        # Getting the index name.
        idx_name = '%s_%s_id' % (db_table, self.column)
        
        sql = style.SQL_KEYWORD('CREATE SPATIAL INDEX ') + \
              style.SQL_TABLE(qn(idx_name)) + \
              style.SQL_KEYWORD(' ON ') + \
              style.SQL_TABLE(qn(db_table)) + '(' + \
              style.SQL_FIELD(qn(self.column)) + ');'
        return sql

    def _post_create_sql(self, style, db_table):
        """
        Returns SQL that will be executed after the model has been
        created.
        """
        # Getting the geometric index for this Geometry column.
        if self._index:
            return (self._geom_index(style, db_table),)
        else:
            return ()

    def db_type(self):
        "The OpenGIS name is returned for the MySQL database column type."
        return self._geom
        
    def get_db_prep_lookup(self, lookup_type, value):
        """
        Returns field's value prepared for database lookup, accepts WKT and 
        GEOS Geometries for the value.
        """
        if lookup_type in MYSQL_GIS_TERMS:
            # special case for isnull lookup
            if lookup_type == 'isnull': return GeoFieldSQL([], [])

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

            return GeoFieldSQL(['%s(%%s)' % GEOM_FROM_TEXT], [value])

        else:
            raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def get_db_prep_save(self, value):
        "Prepares the value for saving in the database."
        if not bool(value): return None
        if isinstance(value, GEOSGeometry):
            return value
        else:
            raise TypeError('Geometry Proxy should only return GEOSGeometry objects.')

    def get_placeholder(self, value):
        """
        Nothing special happens here because MySQL does not support transformations.
        """
        return '%s(%%s)' % GEOM_FROM_TEXT
