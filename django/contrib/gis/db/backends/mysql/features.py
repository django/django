from django.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from django.db.backends.mysql.features import DatabaseFeatures as MySQLDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseSpatialFeatures, MySQLDatabaseFeatures):
    empty_intersection_returns_none = False
    has_spatialrefsys_table = False
    supports_add_srs_entry = False
    supports_distance_geodetic = False
    supports_length_geodetic = False
    supports_area_geodetic = False
    supports_transform = False
    supports_null_geometries = False
    supports_num_points_poly = False
    unsupported_geojson_options = {"crs"}

    @cached_property
    def supports_geometry_field_unique_index(self):
        # Not supported in MySQL since
        # https://dev.mysql.com/worklog/task/?id=11808
        return self.connection.mysql_is_mariadb
