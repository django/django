# The Django base Field class.
from django.db.models.fields import Field
from django.contrib.gis.db.models.postgis import POSTGIS_TERMS

# Creates the SQL to add the model to the database. 
def _add_geom(geom, srid, style, model, field, dim=2):
    # Constructing the AddGeometryColumn(...) command -- the style
    # object is passed in from the management module and is used
    # to syntax highlight the command for 'sqlall'
    sql = style.SQL_KEYWORD('SELECT ') + \
          style.SQL_TABLE('AddGeometryColumn') + "('" + \
          style.SQL_TABLE(model) + "', '" + \
          style.SQL_FIELD(field) + "', " + \
          style.SQL_FIELD(str(srid)) + ", '" + \
          style.SQL_COLTYPE(geom) + "', " + \
          style.SQL_KEYWORD(str(dim)) + \
          ');'
    return sql

# Creates an index for the given geometry.
def _geom_index(geom, style, model, field,
                index_type='GIST',
                index_opts='GIST_GEOMETRY_OPTS'):
    sql = style.SQL_KEYWORD('CREATE INDEX ') + \
          style.SQL_FIELD(field + '_idx') + \
          style.SQL_KEYWORD(' ON ') + \
          style.SQL_TABLE(model) + \
          style.SQL_KEYWORD(' USING ') + \
          style.SQL_COLTYPE(index_type) + ' ( ' + \
          style.SQL_FIELD(field) + ' ' + \
          style.SQL_KEYWORD(index_opts) + ' );'
    return sql

class GeometryField(Field):
    "The base GIS field -- maps to the OpenGIS Geometry type."

    # The OpenGIS Geometry name.
    _geom = 'GEOMETRY'

    def __init__(self, srid=4326, index=False, **kwargs):
        # Calling the Field initialization function first
        super(GeometryField, self).__init__(**kwargs)

        # The SRID for the geometry, defaults to 4326
        self._srid = srid
        self._index = index

    def get_internal_type(self):
        return "NoField"
    
    def _post_create_sql(self, *args, **kwargs):
        """Returns SQL that will be executed after the model has been created.  Geometry
        columns must be added after creation with the PostGIS AddGeometryColumn() function."""
        post_sql = _add_geom(self._geom, self._srid, *args, **kwargs)
        if self._index:
            # Creating geometry indices doesn't yet work.
            #return '%s\n%s' % (post_sql, _geom_index(self._geom, *args, **kwargs))
            return post_sql
        else:
            return post_sql

    def get_db_prep_lookup(self, lookup_type, value):
        """Returns field's value prepared for database lookup; the SRID of the geometry is
        included by default in these queries."""
        if lookup_type in POSTGIS_TERMS:
            return ['SRID=%d;%s' % (self._srid, value)]
        raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def get_db_prep_save(self, value):
        "Making sure the SRID is included before saving."
        return 'SRID=%d;%s' % (self._srid, value)
    
# The OpenGIS Geometry Type Fields
class PointField(GeometryField):
    _geom = 'POINT'

class LineString(GeometryField):
    _geom = 'LINESTRING'

class PolygonField(GeometryField):
    _geom = 'POLYGON'

class MultiPointField(GeometryField):
    _geom = 'MULTIPOINT'

class MultiLineStringField(GeometryField):
    _geom = 'MULTILINESTRING'

class MultiPolygonField(GeometryField):
    _geom = 'MULTIPOLYGON'

class GeometryCollectionField(GeometryField):
    _geom = 'GEOMETRYCOLLECTION'
