"""
SQL functions reference lists:
http://www.gaia-gis.it/spatialite-3.0.0-BETA/spatialite-sql-3.0.0.html
https://web.archive.org/web/20130407175746/http://www.gaia-gis.it/gaia-sins/spatialite-sql-4.0.0.html
http://www.gaia-gis.it/gaia-sins/spatialite-sql-4.2.1.html
"""
import re
import sys

from django.contrib.gis.db.backends.base.operations import \
    BaseSpatialOperations
from django.contrib.gis.db.backends.spatialite.adapter import SpatiaLiteAdapter
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.db.models import aggregates
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Distance
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.sqlite3.operations import DatabaseOperations
from django.utils import six
from django.utils.functional import cached_property


class SpatiaLiteOperations(BaseSpatialOperations, DatabaseOperations):
    name = 'spatialite'
    spatialite = True
    version_regex = re.compile(r'^(?P<major>\d)\.(?P<minor1>\d)\.(?P<minor2>\d+)')

    Adapter = SpatiaLiteAdapter

    area = 'Area'
    centroid = 'Centroid'
    collect = 'Collect'
    contained = 'MbrWithin'
    difference = 'Difference'
    distance = 'Distance'
    envelope = 'Envelope'
    extent = 'Extent'
    geojson = 'AsGeoJSON'
    gml = 'AsGML'
    intersection = 'Intersection'
    kml = 'AsKML'
    length = 'GLength'  # OpenGis defines Length, but this conflicts with an SQLite reserved keyword
    makeline = 'MakeLine'
    num_geom = 'NumGeometries'
    num_points = 'NumPoints'
    point_on_surface = 'PointOnSurface'
    scale = 'ScaleCoords'
    svg = 'AsSVG'
    sym_difference = 'SymDifference'
    transform = 'Transform'
    translate = 'ShiftCoords'
    union = 'GUnion'  # OpenGis defines Union, but this conflicts with an SQLite reserved keyword
    unionagg = 'GUnion'

    from_text = 'GeomFromText'
    from_wkb = 'GeomFromWKB'
    select = 'AsText(%s)'

    gis_operators = {
        'equals': SpatialOperator(func='Equals'),
        'disjoint': SpatialOperator(func='Disjoint'),
        'touches': SpatialOperator(func='Touches'),
        'crosses': SpatialOperator(func='Crosses'),
        'within': SpatialOperator(func='Within'),
        'overlaps': SpatialOperator(func='Overlaps'),
        'contains': SpatialOperator(func='Contains'),
        'intersects': SpatialOperator(func='Intersects'),
        'relate': SpatialOperator(func='Relate'),
        # Returns true if B's bounding box completely contains A's bounding box.
        'contained': SpatialOperator(func='MbrWithin'),
        # Returns true if A's bounding box completely contains B's bounding box.
        'bbcontains': SpatialOperator(func='MbrContains'),
        # Returns true if A's bounding box overlaps B's bounding box.
        'bboverlaps': SpatialOperator(func='MbrOverlaps'),
        # These are implemented here as synonyms for Equals
        'same_as': SpatialOperator(func='Equals'),
        'exact': SpatialOperator(func='Equals'),

        'distance_gt': SpatialOperator(func='Distance', op='>'),
        'distance_gte': SpatialOperator(func='Distance', op='>='),
        'distance_lt': SpatialOperator(func='Distance', op='<'),
        'distance_lte': SpatialOperator(func='Distance', op='<='),
    }

    disallowed_aggregates = (aggregates.Extent3D,)

    @cached_property
    def function_names(self):
        return {
            'Length': 'ST_Length',
            'Reverse': 'ST_Reverse',
            'Scale': 'ScaleCoords',
            'Translate': 'ST_Translate' if self.spatial_version >= (3, 1, 0) else 'ShiftCoords',
            'Union': 'ST_Union',
        }

    @cached_property
    def unsupported_functions(self):
        unsupported = {'BoundingCircle', 'ForceRHR', 'IsValid', 'MakeValid', 'MemSize'}
        if self.spatial_version < (3, 1, 0):
            unsupported.add('SnapToGrid')
        if self.spatial_version < (4, 0, 0):
            unsupported.update({'Perimeter', 'Reverse'})
        elif not self.lwgeom_version():
            unsupported.add('GeoHash')
        return unsupported

    @cached_property
    def spatial_version(self):
        """Determine the version of the SpatiaLite library."""
        try:
            version = self.spatialite_version_tuple()[1:]
        except Exception as msg:
            new_msg = (
                'Cannot determine the SpatiaLite version for the "%s" '
                'database (error was "%s").  Was the SpatiaLite initialization '
                'SQL loaded on this database?') % (self.connection.settings_dict['NAME'], msg)
            six.reraise(ImproperlyConfigured, ImproperlyConfigured(new_msg), sys.exc_info()[2])
        if version < (3, 0, 0):
            raise ImproperlyConfigured('GeoDjango only supports SpatiaLite versions 3.0.0 and above.')
        return version

    def convert_extent(self, box, srid):
        """
        Convert the polygon data received from SpatiaLite to min/max values.
        """
        if box is None:
            return None
        shell = Geometry(box, srid).shell
        xmin, ymin = shell[0][:2]
        xmax, ymax = shell[2][:2]
        return (xmin, ymin, xmax, ymax)

    def convert_geom(self, wkt, geo_field):
        """
        Converts geometry WKT returned from a SpatiaLite aggregate.
        """
        if wkt:
            return Geometry(wkt, geo_field.srid)
        else:
            return None

    def geo_db_type(self, f):
        """
        Returns None because geometry columns are added via the
        `AddGeometryColumn` stored procedure on SpatiaLite.
        """
        return None

    def get_distance(self, f, value, lookup_type, **kwargs):
        """
        Returns the distance parameters for the given geometry field,
        lookup value, and lookup type.  SpatiaLite only supports regular
        cartesian-based queries (no spheroid/sphere calculations for point
        geometries like PostGIS).
        """
        if not value:
            return []
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                raise ValueError('SpatiaLite does not support distance queries on '
                                 'geometry fields with a geodetic coordinate system. '
                                 'Distance objects; use a numeric value of your '
                                 'distance in degrees instead.')
            else:
                dist_param = getattr(value, Distance.unit_attname(f.units_name(self.connection)))
        else:
            dist_param = value
        return [dist_param]

    def get_geom_placeholder(self, f, value, compiler):
        """
        Provides a proper substitution value for Geometries that are not in the
        SRID of the field.  Specifically, this routine will substitute in the
        Transform() and GeomFromText() function call(s).
        """
        def transform_value(value, srid):
            return not (value is None or value.srid == srid)
        if hasattr(value, 'as_sql'):
            if transform_value(value, f.srid):
                placeholder = '%s(%%s, %s)' % (self.transform, f.srid)
            else:
                placeholder = '%s'
            # No geometry value used for F expression, substitute in
            # the column name instead.
            sql, _ = compiler.compile(value)
            return placeholder % sql
        else:
            if transform_value(value, f.srid):
                # Adding Transform() to the SQL placeholder.
                return '%s(%s(%%s,%s), %s)' % (self.transform, self.from_text, value.srid, f.srid)
            else:
                return '%s(%%s,%s)' % (self.from_text, f.srid)

    def _get_spatialite_func(self, func):
        """
        Helper routine for calling SpatiaLite functions and returning
        their result.
        Any error occurring in this method should be handled by the caller.
        """
        cursor = self.connection._cursor()
        try:
            cursor.execute('SELECT %s' % func)
            row = cursor.fetchone()
        finally:
            cursor.close()
        return row[0]

    def geos_version(self):
        "Returns the version of GEOS used by SpatiaLite as a string."
        return self._get_spatialite_func('geos_version()')

    def proj4_version(self):
        "Returns the version of the PROJ.4 library used by SpatiaLite."
        return self._get_spatialite_func('proj4_version()')

    def lwgeom_version(self):
        """Return the version of LWGEOM library used by SpatiaLite."""
        return self._get_spatialite_func('lwgeom_version()')

    def spatialite_version(self):
        "Returns the SpatiaLite library version as a string."
        return self._get_spatialite_func('spatialite_version()')

    def spatialite_version_tuple(self):
        """
        Returns the SpatiaLite version as a tuple (version string, major,
        minor, subminor).
        """
        version = self.spatialite_version()

        m = self.version_regex.match(version)
        if m:
            major = int(m.group('major'))
            minor1 = int(m.group('minor1'))
            minor2 = int(m.group('minor2'))
        else:
            raise Exception('Could not parse SpatiaLite version string: %s' % version)

        return (version, major, minor1, minor2)

    def spatial_aggregate_name(self, agg_name):
        """
        Returns the spatial aggregate SQL template and function for the
        given Aggregate instance.
        """
        agg_name = 'unionagg' if agg_name.lower() == 'union' else agg_name.lower()
        return getattr(self, agg_name)

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        from django.contrib.gis.db.backends.spatialite.models import SpatialiteGeometryColumns
        return SpatialiteGeometryColumns

    def spatial_ref_sys(self):
        from django.contrib.gis.db.backends.spatialite.models import SpatialiteSpatialRefSys
        return SpatialiteSpatialRefSys

    def get_db_converters(self, expression):
        converters = super(SpatiaLiteOperations, self).get_db_converters(expression)
        if hasattr(expression.output_field, 'geom_type'):
            converters.append(self.convert_geometry)
        return converters

    def convert_geometry(self, value, expression, connection, context):
        if value:
            value = Geometry(value)
            if 'transformed_srid' in context:
                value.srid = context['transformed_srid']
        return value
