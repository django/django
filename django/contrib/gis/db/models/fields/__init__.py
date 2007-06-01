# The Django base Field class.
from django.db.models.fields import Field
from django.contrib.gis.db.models.postgis import POSTGIS_TERMS, quotename
from django.contrib.gis.oldforms import WKTField
from django.utils.functional import curry
from django.contrib.gis.geos import GEOSGeometry, GEOSException

#TODO: Flesh out widgets.
#TODO: GEOS and GDAL/OGR operations through fields as proxy.
#TODO: pythonic usage, like "for point in zip.polygon" and "if point in polygon".

class GeometryField(Field):
    "The base GIS field -- maps to the OpenGIS Specification Geometry type."

    # The OpenGIS Geometry name.
    _geom = 'GEOMETRY'

    def __init__(self, srid=4326, index=True, dim=2, **kwargs):
        """The initialization function for geometry fields.  Takes the following
        as keyword arguments:

          srid  - The spatial reference system identifier.  An OGC standard.
                  Defaults to 4326 (WGS84)

          index - Indicates whether to create a GiST index.  Defaults to True.
                  Set this instead of 'db_index' for geographic fields since index
                  creation is different for geometry columns.
                  
          dim   - The number of dimensions for this geometry.  Defaults to 2.
        """
        self._index = index
        self._srid = srid
        self._dim = dim
        super(GeometryField, self).__init__(**kwargs) # Calling the parent initializtion function

    def _add_geom(self, style, db_table, field):
        """Constructs the addition of the geometry to the table using the
        AddGeometryColumn(...) PostGIS (and OGC standard) function.

        Takes the style object (provides syntax highlighting) as well as the
         database table and field.
        """
        sql = style.SQL_KEYWORD('SELECT ') + \
              style.SQL_TABLE('AddGeometryColumn') + '(' + \
              style.SQL_TABLE(quotename(db_table)) + ', ' + \
              style.SQL_FIELD(quotename(field)) + ', ' + \
              style.SQL_FIELD(str(self._srid)) + ', ' + \
              style.SQL_COLTYPE(quotename(self._geom)) + ', ' + \
              style.SQL_KEYWORD(str(self._dim)) + ');'
        return sql

    def _geom_index(self, style, db_table, field,
                    index_type='GIST', index_opts='GIST_GEOMETRY_OPS'):
        "Creates a GiST index for this geometry field."
        sql = style.SQL_KEYWORD('CREATE INDEX ') + \
              style.SQL_TABLE(quotename('%s_%s_id' % (db_table, field), dbl=True)) + \
              style.SQL_KEYWORD(' ON ') + \
              style.SQL_TABLE(quotename(db_table, dbl=True)) + \
              style.SQL_KEYWORD(' USING ') + \
              style.SQL_COLTYPE(index_type) + ' ( ' + \
              style.SQL_FIELD(quotename(field, dbl=True)) + ' ' + \
              style.SQL_KEYWORD(index_opts) + ' );'
        return sql

    def _post_create_sql(self, style, db_table, field):
        """Returns SQL that will be executed after the model has been
        created. Geometry columns must be added after creation with the
        PostGIS AddGeometryColumn() function."""

        # Getting the AddGeometryColumn() SQL necessary to create a PostGIS
        # geometry field.
        post_sql = self._add_geom(style, db_table, field)

        # If the user wants to index this data, then get the indexing SQL as well.
        if self._index:
            return '%s\n%s' % (post_sql, self._geom_index(style, db_table, field))
        else:
            return post_sql

    def contribute_to_class(self, cls, name):
        super(GeometryField, self).contribute_to_class(cls, name)

        # Adding needed accessor functions
        setattr(cls, 'get_%s_geos' % self.name, curry(cls._get_GEOM_geos, field=self))
        setattr(cls, 'get_%s_ogr' % self.name, curry(cls._get_GEOM_ogr, field=self, srid=self._srid))
        setattr(cls, 'get_%s_wkt' % self.name, curry(cls._get_GEOM_wkt, field=self))
        setattr(cls, 'get_%s_centroid' % self.name, curry(cls._get_GEOM_centroid, field=self))
        setattr(cls, 'get_%s_area' % self.name, curry(cls._get_GEOM_area, field=self))
        
    def get_internal_type(self):
        return "NoField"
                                                                
    def get_db_prep_lookup(self, lookup_type, value):
        """Returns field's value prepared for database lookup; the SRID of the geometry is
        included by default in these queries."""
        if lookup_type in POSTGIS_TERMS:
            return ['SRID=%d;%s' % (self._srid, value)]
        raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def get_db_prep_save(self, value):
        "Making sure the SRID is included before saving."
        return 'SRID=%d;%s' % (self._srid, value)

    def get_manipulator_field_objs(self):
        "Using the WKTField (defined above) to be our manipulator."
        return [WKTField]

# The OpenGIS Geometry Type Fields
class PointField(GeometryField):
    _geom = 'POINT'

class LineStringField(GeometryField):
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
