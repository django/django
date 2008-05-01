from itertools import izip
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.models.query import sql, QuerySet, Q

from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.db.models.fields import GeometryField, PointField
from django.contrib.gis.db.models.sql import GeoQuery, GeoWhereNode
from django.contrib.gis.geos import GEOSGeometry, Point
qn = connection.ops.quote_name

# For backwards-compatibility; Q object should work just fine
# after queryset-refactor.
class GeoQ(Q): pass

class GeomSQL(object):
    "Simple wrapper object for geometric SQL."
    def __init__(self, geo_sql):
        self.sql = geo_sql
    
    def as_sql(self, *args, **kwargs):
        return self.sql

class GeoQuerySet(QuerySet):
    "The Geographic QuerySet."

    def __init__(self, model=None, query=None):
        super(GeoQuerySet, self).__init__(model=model, query=query)
        self.query = query or GeoQuery(self.model, connection)

    def distance(self, *args, **kwargs):
        """
        Returns the distance from the given geographic field name to the
        given geometry in a `distance` attribute on each element of the
        GeoQuerySet.
        """
        DISTANCE = SpatialBackend.distance
        if not DISTANCE:
            raise ImproperlyConfigured('Distance() stored proecedure not available.')

        # Getting the geometry field and GEOSGeometry object to base distance
        # calculations from.
        nargs = len(args)
        if nargs == 1:
            field_name = None
            geom = args[0]
        elif nargs == 2:
            field_name, geom = args
        else:
            raise ValueError('Maximum two arguments allowed for `distance` aggregate.')

        # Getting the GeometryField and quoted column.
        geo_field = self.query._geo_field(field_name)
        if not geo_field:
            raise TypeError('Distance output only available on GeometryFields.')
        geo_col = self.query._field_column(geo_field)

        # Using the field's get_db_prep_lookup() to get any needed
        # transformation SQL -- we pass in a 'dummy' `contains`
        # `distance_lte` lookup type.
        where, params = geo_field.get_db_prep_lookup('distance_lte', (geom, 0))
        if SpatialBackend.oracle:
            # The `tolerance` keyword may be used for Oracle; the tolerance is 
            # in meters -- a default of 5 centimeters is used.
            tolerance = kwargs.get('tolerance', 0.05)
            dist_select = {'distance' : '%s(%s, %s, %s)' % (DISTANCE, geo_col, where[0], tolerance)}
        else:
            if len(where) == 3:
                # Spherical distance calculation was requested (b/c spheroid 
                # parameter was attached) However, the PostGIS ST_distance_spheroid() 
                # procedure may only do queries from point columns to point geometries
                # some error checking is required.
                if not isinstance(geo_field, PointField): 
                    raise TypeError('Spherical distance calculation only supported on PointFields.')
                if not isinstance(GEOSGeometry(buffer(params[0].wkb)), Point):
                    raise TypeError('Spherical distance calculation only supported with Point Geometry parameters')

                # Call to distance_spheroid() requires the spheroid as well.
                dist_sql = '%s(%s, %s, %s)' % (SpatialBackend.distance_spheroid, geo_col, where[0], where[1])
            else:
                dist_sql = '%s(%s, %s)' % (DISTANCE, geo_col, where[0])
            dist_select = {'distance' : dist_sql}
        return self.extra(select=dist_select, select_params=params)

    def extent(self, field_name=None):
        """
        Returns the extent (aggregate) of the features in the GeoQuerySet.  The
        extent will be returned as a 4-tuple, consisting of (xmin, ymin, xmax, ymax).
        """
        EXTENT = SpatialBackend.extent
        if not EXTENT:
            raise ImproperlyConfigured('Extent stored procedure not available.')

        # Getting the GeometryField and quoted column.
        geo_field = self.query._geo_field(field_name)
        if not geo_field:
            raise TypeError('Extent information only available on GeometryFields.')
        geo_col = self.query._field_column(geo_field)

        # Constructing the query that will select the extent.
        extent_sql = '%s(%s)' % (EXTENT, geo_col)

        self.query.select = [GeomSQL(extent_sql)]
        self.query.select_fields = [None]
        try:
            esql, params = self.query.as_sql()
        except sql.datastructures.EmptyResultSet:
            return None        

        # Getting a cursor, executing the query, and extracting the returned
        # value from the extent function.
        cursor = connection.cursor()
        cursor.execute(esql, params)
        box = cursor.fetchone()[0]

        if box: 
            # TODO: Parsing of BOX3D, Oracle support (patches welcome!)
            #  Box text will be something like "BOX(-90.0 30.0, -85.0 40.0)"; 
            #  parsing out and returning as a 4-tuple.
            ll, ur = box[4:-1].split(',')
            xmin, ymin = map(float, ll.split())
            xmax, ymax = map(float, ur.split())
            return (xmin, ymin, xmax, ymax)
        else: 
            return None

    def gml(self, field_name=None, precision=8, version=2):
        """
        Returns GML representation of the given field in a `gml` attribute
        on each element of the GeoQuerySet.
        """
        # Is GML output supported?
        ASGML = SpatialBackend.as_gml
        if not ASGML:
            raise ImproperlyConfigured('AsGML() stored procedure not available.')
 
        # Getting the GeometryField and quoted column.
        geo_field = self.query._geo_field(field_name)
        if not geo_field:
            raise TypeError('GML output only available on GeometryFields.')
        geo_col = self.query._field_column(geo_field)

        if SpatialBackend.oracle:
            gml_select = {'gml':'%s(%s)' % (ASGML, geo_col)}
        elif SpatialBackend.postgis:
            # PostGIS AsGML() aggregate function parameter order depends on the 
            # version -- uggh.
            major, minor1, minor2 = SpatialBackend.version
            if major >= 1 and (minor1 > 3 or (minor1 == 3 and minor2 > 1)):
                gml_select = {'gml':'%s(%s,%s,%s)' % (ASGML, version, geo_col, precision)}
            else:
                gml_select = {'gml':'%s(%s,%s,%s)' % (ASGML, geo_col, precision, version)}

        # Adding GML function call to SELECT part of the SQL.
        return self.extra(select=gml_select)

    def kml(self, field_name=None, precision=8):
        """
        Returns KML representation of the given field name in a `kml`
        attribute on each element of the GeoQuerySet.
        """
        # Is KML output supported?
        ASKML = SpatialBackend.as_kml
        if not ASKML:
            raise ImproperlyConfigured('AsKML() stored procedure not available.')

        # Getting the GeometryField and quoted column.
        geo_field = self.query._geo_field(field_name)
        if not geo_field:
            raise TypeError('KML output only available on GeometryFields.')

        geo_col = self.query._field_column(geo_field)

        # Adding the AsKML function call to SELECT part of the SQL.
        return self.extra(select={'kml':'%s(%s,%s)' % (ASKML, geo_col, precision)})

    def transform(self, field_name=None, srid=4326):
        """
        Transforms the given geometry field to the given SRID.  If no SRID is
        provided, the transformation will default to using 4326 (WGS84).
        """
        # Getting the geographic field.
        TRANSFORM = SpatialBackend.transform
        if not TRANSFORM:
            raise ImproperlyConfigured('Transform stored procedure not available.')

        # `field_name` is first for backwards compatibility; but we want to
        # be able to take integer srid as first parameter.
        if isinstance(field_name, (int, long)):
            srid = field_name
            field_name = None

        # Getting the GeometryField and quoted column.
        geo_field = self.query._geo_field(field_name)
        if not geo_field:
            raise TypeError('%s() only available for GeometryFields' % TRANSFORM)
        
        # Getting the selection SQL for the given geograph
        field_col = self._geocol_select(geo_field, field_name)

        # Why cascading substitutions? Because spatial backends like
        # Oracle and MySQL already require a function call to convert to text, thus
        # when there's also a transformation we need to cascade the substitutions.
        # For example, 'SDO_UTIL.TO_WKTGEOMETRY(SDO_CS.TRANSFORM( ... )'
        geo_col = self.query.custom_select.get(geo_field, field_col)
        
        # Setting the key for the field's column with the custom SELECT SQL to
        # override the geometry column returned from the database.
        if SpatialBackend.oracle:
            custom_sel = '%s(%s, %s)' % (TRANSFORM, geo_col, srid)
            self.query.ewkt = srid
        else:
            custom_sel = '%s(%s, %s)' % (TRANSFORM, geo_col, srid)
        self.query.custom_select[geo_field] = custom_sel
        return self._clone()

    def union(self, field_name=None, tolerance=0.0005):
        """
        Performs an aggregate union on the given geometry field.  Returns
        None if the GeoQuerySet is empty.  The `tolerance` keyword is for
        Oracle backends only.
        """
        # Making sure backend supports the Union stored procedure
        UNION = SpatialBackend.union
        if not UNION:
            raise ImproperlyConfigured('Union stored procedure not available.')

        # Getting the GeometryField and quoted column.
        geo_field = self.query._geo_field(field_name)
        if not geo_field:
            raise TypeError('Aggregate Union only available on GeometryFields.')
        geo_col = self.query._field_column(geo_field)

        # Replacing the select with a call to the ST_Union stored procedure
        #  on the geographic field column.
        if SpatialBackend.oracle:
            union_sql = '%s' % SpatialBackend.select
            union_sql = union_sql % ('%s(SDOAGGRTYPE(%s,%s))' % (UNION, geo_col, tolerance))
        else:
            union_sql = '%s(%s)' % (UNION, geo_col)

        # Only want the union SQL to be selected.
        self.query.select = [GeomSQL(union_sql)]
        self.query.select_fields = [GeometryField]
        try:
            usql, params = self.query.as_sql()
        except sql.datastructures.EmptyResultSet:
            return None

        # Getting a cursor, executing the query.
        cursor = connection.cursor()
        cursor.execute(usql, params)
        if SpatialBackend.oracle:
            # On Oracle have to read out WKT from CLOB first.
            clob = cursor.fetchone()[0]
            if clob: u = clob.read()
            else: u = None
        else:
            u = cursor.fetchone()[0]
        
        if u: return GEOSGeometry(u)
        else: return None

    # Private API utilities, subject to change.
    def _geocol_select(self, geo_field, field_name):
        """
        Helper routine for constructing the SQL to select the geographic
        column.  Takes into account if the geographic field is in a
        ForeignKey relation to the current model.
        """
        # Is this operation going to be on a related geographic field?
        if not geo_field in self.model._meta.fields:
            # If so, it'll have to be added to the select related information
            # (e.g., if 'location__point' was given as the field name).
            self.query.add_select_related([field_name])
            self.query.pre_sql_setup()
            rel_table, rel_col = self.query.related_select_cols[self.query.related_select_fields.index(geo_field)]
            return self.query._field_column(geo_field, rel_table)
        else:
            return self.query._field_column(geo_field)
