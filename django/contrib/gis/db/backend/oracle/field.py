import re
from types import StringType, UnicodeType
from django.db import connection
from django.db.backends.util import truncate_name
from django.db.models.fields import Field # Django base Field class
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.backend.util import GeoFieldSQL
from django.contrib.gis.db.backend.oracle.adaptor import OracleSpatialAdaptor
from django.contrib.gis.db.backend.oracle.query import ORACLE_SPATIAL_TERMS, TRANSFORM

# Quotename & geographic quotename, respectively.
qn = connection.ops.quote_name
def gqn(value):
    if isinstance(value, UnicodeType): value = value.encode('ascii')
    return "'%s'" % value

class OracleSpatialField(Field):
    """
    The backend-specific geographic field for Oracle Spatial.
    """

    empty_strings_allowed = False

    def __init__(self, extent=(-180.0, -90.0, 180.0, 90.0), tolerance=0.00005, **kwargs):
        """
        Oracle Spatial backend needs to have the extent -- for projected coordinate
        systems _you must define the extent manually_, since the coordinates are
        for geodetic systems.  The `tolerance` keyword specifies the tolerance
        for error (in meters).
        """
        # Oracle Spatial specific keyword arguments.
        self._extent = extent
        self._tolerance = tolerance
        # Calling the Django field initialization.
        super(OracleSpatialField, self).__init__(**kwargs)

    def _add_geom(self, style, db_table):
        """
        Adds this geometry column into the Oracle USER_SDO_GEOM_METADATA
        table.
        """

        # Checking the dimensions.
        # TODO: Add support for 3D geometries.
        if self._dim != 2:
            raise Exception('3D geometries not yet supported on Oracle Spatial backend.')

        # Constructing the SQL that will be used to insert information about
        # the geometry column into the USER_GSDO_GEOM_METADATA table.
        meta_sql = style.SQL_KEYWORD('INSERT INTO ') + \
                   style.SQL_TABLE('USER_SDO_GEOM_METADATA') + \
                   ' (%s, %s, %s, %s)\n  ' % tuple(map(qn, ['TABLE_NAME', 'COLUMN_NAME', 'DIMINFO', 'SRID'])) + \
                   style.SQL_KEYWORD(' VALUES ') + '(\n    ' + \
                   style.SQL_TABLE(gqn(db_table)) + ',\n    ' + \
                   style.SQL_FIELD(gqn(self.column)) + ',\n    ' + \
                   style.SQL_KEYWORD("MDSYS.SDO_DIM_ARRAY") + '(\n      ' + \
                   style.SQL_KEYWORD("MDSYS.SDO_DIM_ELEMENT") + \
                   ("('LONG', %s, %s, %s),\n      " % (self._extent[0], self._extent[2], self._tolerance)) + \
                   style.SQL_KEYWORD("MDSYS.SDO_DIM_ELEMENT") + \
                   ("('LAT', %s, %s, %s)\n    ),\n" % (self._extent[1], self._extent[3], self._tolerance)) + \
                   '    %s\n  );' % self._srid
        return meta_sql

    def _geom_index(self, style, db_table):
        "Creates an Oracle Geometry index (R-tree) for this geometry field."

        # Getting the index name, Oracle doesn't allow object
        # names > 30 characters.
        idx_name = truncate_name('%s_%s_id' % (db_table, self.column), 30)
        
        sql = style.SQL_KEYWORD('CREATE INDEX ') + \
              style.SQL_TABLE(qn(idx_name)) + \
              style.SQL_KEYWORD(' ON ') + \
              style.SQL_TABLE(qn(db_table)) + '(' + \
              style.SQL_FIELD(qn(self.column)) + ') ' + \
              style.SQL_KEYWORD('INDEXTYPE IS ') + \
              style.SQL_TABLE('MDSYS.SPATIAL_INDEX') + ';'
        return sql

    def _post_create_sql(self, style, db_table):
        """
        Returns SQL that will be executed after the model has been
        created.
        """
        # Getting the meta geometry information.
        post_sql = self._add_geom(style, db_table)

        # Getting the geometric index for this Geometry column.
        if self._index:
            return (post_sql, self._geom_index(style, db_table))
        else:
            return (post_sql,)

    def db_type(self):
        "The Oracle geometric data type is MDSYS.SDO_GEOMETRY."
        return 'MDSYS.SDO_GEOMETRY'
        
    def get_db_prep_lookup(self, lookup_type, value):
        """
        Returns field's value prepared for database lookup, accepts WKT and 
        GEOS Geometries for the value.
        """
        if lookup_type in ORACLE_SPATIAL_TERMS:
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

            # Getting the SRID of the geometry, or defaulting to that of the field if
            # it is None.
            if value.srid is None: srid = self._srid
            else: srid = value.srid
            
            # The adaptor will be used by psycopg2 for quoting the WKT.
            adapt = OracleSpatialAdaptor(value)
            if srid != self._srid:
                # Adding the necessary string substitutions and parameters
                # to perform a geometry transformation.
                return GeoFieldSQL(['%s(SDO_GEOMETRY(%%s, %s), %%s)' % (TRANSFORM, srid)],
                                   [adapt, self._srid])
            else:
                return GeoFieldSQL(['SDO_GEOMETRY(%%s, %s)' % srid], [adapt])

        else:
            raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def get_db_prep_save(self, value):
        "Prepares the value for saving in the database."
        if not bool(value):
            # Return an empty string for NULL -- but this doesn't work yet.
            return ''
        if isinstance(value, GEOSGeometry):
            return OracleSpatialAdaptor(value)
        else:
            raise TypeError('Geometry Proxy should only return GEOSGeometry objects.')

    def get_placeholder(self, value):
        """
        Provides a proper substitution value for Geometries that are not in the
        SRID of the field.  Specifically, this routine will substitute in the
        SDO_CS.TRANSFORM() function call.
        """
        if isinstance(value, GEOSGeometry) and value.srid != self._srid:
            # Adding Transform() to the SQL placeholder.
            return '%s(SDO_GEOMETRY(%%s, %s), %s)' % (TRANSFORM, value.srid, self._srid)
        elif value is None:
            return '%s'
        else:
            return 'SDO_GEOMETRY(%%s, %s)' % self._srid
