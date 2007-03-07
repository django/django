from django.db import models
from django.db.models.fields import Field
#from GeoTypes import Point

# Creates the SQL to add the model to the database.  Defaults to using an
# SRID of 4326 (WGS84 Datum -- 'normal' lat/lon coordinates)
def _add_geom(geom, srid, style, model, field, dim=2):
    from django.db import backend

    # Constructing the AddGeometryColumn(...) command -- the style
    # object is passed in from the management module and is used
    # to syntax highlight the command for 'sqlall'
    sql = style.SQL_KEYWORD('SELECT ') + \
          style.SQL_TABLE('AddGeometryColumn') + "('" + \
          style.SQL_TABLE(model) + "', '" + \
          style.SQL_FIELD(field) + "', " + \
          style.SQL_FIELD(str(srid)) + ", '" + \
          style.SQL_KEYWORD(geom) + "', " + \
          style.SQL_KEYWORD(str(dim)) + \
          ');'
    return sql

class GeometryField(Field):
    """The base GIS field -- maps to an OpenGIS Geometry type."""
    
    _geom = 'GEOMETRY'
    _srid = 4326
    
    def _post_create_sql(self, *args, **kwargs):
        """Returns SQL that will be executed after the model has been created.  Geometry
        columns must be added after creation with the PostGIS AddGeometryColumn() function."""
        return _add_geom(self._geom, self._srid, *args, **kwargs)

    def get_db_prep_lookup(self, lookup_type, value):
        "Returns field's value prepared for database lookup."
        if lookup_type in ('exact', 'gt', 'gte', 'lt', 'lte', 'month', 'day', 'search', 'overlaps'):
            return [value]
        elif lookup_type in ('range', 'in'):
            return value
        elif lookup_type in ('contains', 'icontains'):
            return ["%%%s%%" % prep_for_like_query(value)]
        elif lookup_type == 'iexact':
            return [prep_for_like_query(value)]
        elif lookup_type in ('startswith', 'istartswith'):
            return ["%s%%" % prep_for_like_query(value)]
        elif lookup_type in ('endswith', 'iendswith'):
            return ["%%%s" % prep_for_like_query(value)]
        elif lookup_type == 'isnull':
            return []
        elif lookup_type == 'year':
            try:
                value = int(value)
            except ValueError:
                raise ValueError("The __year lookup type requires an integer argument")
            return ['%s-01-01 00:00:00' % value, '%s-12-31 23:59:59.999999' % value]
        raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def get_db_prep_save(self, value):
        return 'SRID=%d;%s' % (self._srid, value)
    

class PointField(GeometryField):
    _geom = 'POINT'

class PolygonField(GeometryField):
    _geom = 'POLYGON'

class MultiPolygonField(GeometryField):
    _geom = 'MULTIPOLYGON'

class GeometryManager(models.Manager):
    pass
