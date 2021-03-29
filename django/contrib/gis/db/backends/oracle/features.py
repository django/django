from django.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from django.db.backends.oracle.features import (
    DatabaseFeatures as OracleDatabaseFeatures,
)


class DatabaseFeatures(BaseSpatialFeatures, OracleDatabaseFeatures):
    supports_add_srs_entry = False
    supports_geometry_field_introspection = False
    supports_geometry_field_unique_index = False
    supports_perimeter_geodetic = True
    supports_dwithin_distance_expr = False
    supports_tolerance_parameter = True
    unsupported_geojson_options = {'bbox', 'crs', 'precision'}
