from django.db.backends.mysql.base import *
from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.contrib.gis.db.backends.mysql.creation import MySQLCreation
from django.contrib.gis.db.backends.mysql.introspection import MySQLIntrospection
from django.contrib.gis.db.backends.mysql.operations import MySQLOperations

class DatabaseWrapper(MySQLDatabaseWrapper):

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.creation = MySQLCreation(self)
        self.ops = MySQLOperations()
        self.introspection = MySQLIntrospection(self)
