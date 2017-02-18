from django.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from django.contrib.gis.geos import geos_version_info
from django.db.backends.sqlite3.features import \
    DatabaseFeatures as SQLiteDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseSpatialFeatures, SQLiteDatabaseFeatures):
    supports_distance_geodetic = False
    # SpatiaLite can only count vertices in LineStrings
    supports_num_points_poly = False

    @cached_property
    def supports_initspatialmetadata_in_one_transaction(self):
        # SpatiaLite 4.1+ support initializing all metadata in one transaction
        # which can result in a significant performance improvement when
        # creating the database.
        return self.connection.ops.spatial_version >= (4, 1, 0)

    @cached_property
    def supports_3d_storage(self):
        return geos_version_info()['version'] >= '3.3'
