from django.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from django.db.backends.postgresql.features import \
    DatabaseFeatures as Psycopg2DatabaseFeatures


class DatabaseFeatures(BaseSpatialFeatures, Psycopg2DatabaseFeatures):
    supports_3d_storage = True
    supports_3d_functions = True
    supports_left_right_lookups = True
    supports_raster = True
