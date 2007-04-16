# The Django base Field class.
from django.db.models.fields import Field
from django.contrib.gis.db.models.postgis import POSTGIS_TERMS
from django.contrib.gis.oldforms import WKTField
from django.utils.functional import curry

#TODO: add db.quotename.

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
                index_opts='GIST_GEOMETRY_OPS'):
    sql = style.SQL_KEYWORD('CREATE INDEX ') + \
          style.SQL_TABLE('"%s_%s_id"' % (model, field)) + \
          style.SQL_KEYWORD(' ON ') + \
          style.SQL_TABLE('"%s"' % model) + \
          style.SQL_KEYWORD(' USING ') + \
          style.SQL_COLTYPE(index_type) + ' ( ' + \
          style.SQL_FIELD('"%s"' % field) + ' ' + \
          style.SQL_KEYWORD(index_opts) + ' );'
    return sql

class GeometryField(Field):
    "The base GIS field -- maps to the OpenGIS Geometry type."

    # The OpenGIS Geometry name.
    _geom = 'GEOMETRY'

    def __init__(self, srid=4326, index=False, **kwargs):
        #TODO: SRID a standard, or specific to postgis?
        # Whether or not index this field, defaults to False
        # Why can't we just use db_index? 
        # TODO: Move index creation (and kwarg lookup, and...)
        #  into Field rather than core.management and db.models.query.
        self._index = index

        # The SRID for the geometry, defaults to 4326.
        self._srid = srid

        # Calling the Field initialization function first
        super(GeometryField, self).__init__(**kwargs)


    def contribute_to_class(self, cls, name):
        super(GeometryField, self).contribute_to_class(cls, name)

        # Adding the WKT accessor function for geometry
        setattr(cls, 'get_%s_geos' % self.name, curry(cls._get_GEOM_geos, field=self))
        setattr(cls, 'get_%s_wkt' % self.name, curry(cls._get_GEOM_wkt, field=self))
        setattr(cls, 'get_%s_centroid' % self.name, curry(cls._get_GEOM_centroid, field=self))
        setattr(cls, 'get_%s_area' % self.name, curry(cls._get_GEOM_area, field=self))

    def get_internal_type(self):
        return "NoField"
    
    def _post_create_sql(self, *args, **kwargs):
        """Returns SQL that will be executed after the model has been created.  Geometry
        columns must be added after creation with the PostGIS AddGeometryColumn() function."""

        #TODO: clean up *args/**kwargs.

        # Getting the AddGeometryColumn() SQL necessary to create a PostGIS
        # geometry field.
        post_sql = _add_geom(self._geom, self._srid, *args, **kwargs)

        # If the user wants to index this data, then get the indexing SQL as well.
        if self._index:
            return '%s\n%s' % (post_sql, _geom_index(self._geom, *args, **kwargs))
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
