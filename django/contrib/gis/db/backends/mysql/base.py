from django.db.backends.mysql.base import (
    DatabaseWrapper as MySQLDatabaseWrapper,
    DatabaseFeatures as MySQLDatabaseFeatures,
)
from django.contrib.gis.db.backends.base import BaseSpatialFeatures
from django.contrib.gis.db.backends.mysql.creation import MySQLCreation
from django.contrib.gis.db.backends.mysql.introspection import MySQLIntrospection
from django.contrib.gis.db.backends.mysql.operations import MySQLOperations


class DatabaseFeatures(BaseSpatialFeatures, MySQLDatabaseFeatures):
    has_spatialrefsys_table = False
    supports_num_points_poly = False


class DatabaseWrapper(MySQLDatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.features = DatabaseFeatures(self)
        self.creation = MySQLCreation(self)
        self.ops = MySQLOperations(self)
        self.introspection = MySQLIntrospection(self)
