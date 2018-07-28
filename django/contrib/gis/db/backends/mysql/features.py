from django.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from django.db.backends.mysql.features import (
    DatabaseFeatures as MySQLDatabaseFeatures,
)
from django.utils.functional import cached_property


class DatabaseFeatures(BaseSpatialFeatures, MySQLDatabaseFeatures):
    has_spatialrefsys_table = False
    supports_add_srs_entry = False
    supports_distance_geodetic = False
    supports_length_geodetic = False
    supports_area_geodetic = False
    supports_transform = False
    supports_real_shape_operations = False
    supports_null_geometries = False
    supports_num_points_poly = False

    @cached_property
    def supports_empty_geometry_collection(self):
        return self.connection.mysql_version >= (5, 7, 5)
