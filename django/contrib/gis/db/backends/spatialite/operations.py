"""
SQL functions reference lists:
https://www.gaia-gis.it/gaia-sins/spatialite-sql-4.2.1.html
"""
from django.contrib.gis.db.backends.base.operations import (
    BaseSpatialOperations,
)
from django.contrib.gis.db.backends.spatialite.adapter import SpatiaLiteAdapter
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.db.models import aggregates
from django.contrib.gis.geos.geometry import GEOSGeometry, GEOSGeometryBase
from django.contrib.gis.geos.prototypes.io import wkb_r, wkt_r
from django.contrib.gis.measure import Distance
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.sqlite3.operations import DatabaseOperations
from django.utils.functional import cached_property
from django.utils.version import get_version_tuple


class SpatialiteNullCheckOperator(SpatialOperator):
    def as_sql(self, connection, lookup, template_params, sql_params):
        sql, params = super().as_sql(connection, lookup, template_params, sql_params)
        return '%s > 0' % sql, params


class SpatiaLiteOperations(BaseSpatialOperations, DatabaseOperations):
    name = 'spatialite'
    spatialite = True

    Adapter = SpatiaLiteAdapter

    collect = 'Collect'
    extent = 'Extent'
    makeline = 'MakeLine'
    unionagg = 'GUnion'

    from_text = 'GeomFromText'

    gis_operators = {
        # Binary predicates
        'equals': SpatialiteNullCheckOperator(func='Equals'),
        'disjoint': SpatialiteNullCheckOperator(func='Disjoint'),
        'touches': SpatialiteNullCheckOperator(func='Touches'),
        'crosses': SpatialiteNullCheckOperator(func='Crosses'),
        'within': SpatialiteNullCheckOperator(func='Within'),
        'overlaps': SpatialiteNullCheckOperator(func='Overlaps'),
        'contains': SpatialiteNullCheckOperator(func='Contains'),
        'intersects': SpatialiteNullCheckOperator(func='Intersects'),
        'relate': SpatialiteNullCheckOperator(func='Relate'),
        # Returns true if B's bounding box completely contains A's bounding box.
        'contained': SpatialOperator(func='MbrWithin'),
        # Returns true if A's bounding box completely contains B's bounding box.
        'bbcontains': SpatialOperator(func='MbrContains'),
        # Returns true if A's bounding box overlaps B's bounding box.
        'bboverlaps': SpatialOperator(func='MbrOverlaps'),
        # These are implemented here as synonyms for Equals
        'same_as': SpatialiteNullCheckOperator(func='Equals'),
        'exact': SpatialiteNullCheckOperator(func='Equals'),
        # Distance predicates
        'dwithin': SpatialOperator(func='PtDistWithin'),
    }

    disallowed_aggregates = (aggregates.Extent3D,)

    @cached_property
    def select(self):
        return 'CAST (AsEWKB(%s) AS BLOB)' if self.spatial_version >= (4, 3, 0) else 'AsText(%s)'

    function_names = {
        'Length': 'ST_Length',
        'LineLocatePoint': 'ST_Line_Locate_Point',
        'NumPoints': 'ST_NPoints',
        'Reverse': 'ST_Reverse',
        'Scale': 'ScaleCoords',
        'Translate': 'ST_Translate',
        'Union': 'ST_Union',
    }

    @cached_property
    def unsupported_functions(self):
        unsupported = {'BoundingCircle', 'ForceRHR', 'MemSize'}
        if not self.lwgeom_version():
            unsupported |= {'Azimuth', 'GeoHash', 'IsValid', 'MakeValid'}
        return unsupported

    @cached_property
    def spatial_version(self):
        """Determine the version of the SpatiaLite library."""
        try:
            version = self.spatialite_version_tuple()[1:]
        except Exception as exc:
            raise ImproperlyConfigured(
                'Cannot determine the SpatiaLite version for the "%s" database. '
                'Was the SpatiaLite initialization SQL loaded on this database?' % (
                    self.connection.settings_dict['NAME'],
                )
            ) from exc
        if version < (4, 1, 0):
            raise ImproperlyConfigured('GeoDjango only supports SpatiaLite versions 4.1.0 and above.')
        return version

    def convert_extent(self, box):
        """
        Convert the polygon data received from SpatiaLite to min/max values.
        """
        if box is None:
            return None
        shell = GEOSGeometry(box).shell
        xmin, ymin = shell[0][:2]
        xmax, ymax = shell[2][:2]
        return (xmin, ymin, xmax, ymax)

    def geo_db_type(self, f):
        """
        Return None because geometry columns are added via the
        `AddGeometryColumn` stored procedure on SpatiaLite.
        """
        return None

    def get_distance(self, f, value, lookup_type):
        """
        Return the distance parameters for the given geometry field,
        lookup value, and lookup type.
        """
        if not value:
            return []
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                if lookup_type == 'dwithin':
                    raise ValueError(
                        'Only numeric values of degree units are allowed on '
                        'geographic DWithin queries.'
                    )
                dist_param = value.m
            else:
                dist_param = getattr(value, Distance.unit_attname(f.units_name(self.connection)))
        else:
            dist_param = value
        return [dist_param]

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
        "Return the version of GEOS used by SpatiaLite as a string."
        return self._get_spatialite_func('geos_version()')

    def proj4_version(self):
        "Return the version of the PROJ.4 library used by SpatiaLite."
        return self._get_spatialite_func('proj4_version()')

    def lwgeom_version(self):
        """Return the version of LWGEOM library used by SpatiaLite."""
        return self._get_spatialite_func('lwgeom_version()')

    def spatialite_version(self):
        "Return the SpatiaLite library version as a string."
        return self._get_spatialite_func('spatialite_version()')

    def spatialite_version_tuple(self):
        """
        Return the SpatiaLite version as a tuple (version string, major,
        minor, subminor).
        """
        version = self.spatialite_version()
        return (version,) + get_version_tuple(version)

    def spatial_aggregate_name(self, agg_name):
        """
        Return the spatial aggregate SQL template and function for the
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

    def get_geometry_converter(self, expression):
        geom_class = expression.output_field.geom_class
        if self.spatial_version >= (4, 3, 0):
            read = wkb_r().read

            def converter(value, expression, connection):
                return None if value is None else GEOSGeometryBase(read(value), geom_class)
        else:
            read = wkt_r().read
            srid = expression.output_field.srid
            if srid == -1:
                srid = None

            def converter(value, expression, connection):
                if value is not None:
                    geom = GEOSGeometryBase(read(value), geom_class)
                    if srid:
                        geom.srid = srid
                    return geom
        return converter
