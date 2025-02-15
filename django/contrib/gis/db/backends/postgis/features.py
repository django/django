from thibaud.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from thibaud.db.backends.postgresql.features import (
    DatabaseFeatures as PsycopgDatabaseFeatures,
)


class DatabaseFeatures(BaseSpatialFeatures, PsycopgDatabaseFeatures):
    supports_geography = True
    supports_3d_storage = True
    supports_3d_functions = True
    supports_raster = True
    supports_empty_geometries = True
    empty_intersection_returns_none = False
