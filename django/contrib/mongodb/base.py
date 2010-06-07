from pymongo import Connection

from django.db.backends import BaseDatabaseWrapper
from django.db.backends.signals import connection_created
from django.contrib.mongodb.creation import DatabaseCreation


class DatabaseFeatures(object):
    interprets_empty_strings_as_nulls = False


class DatabaseOperations(object):
    def max_name_length(self):
        return 254
    
    def value_to_db_datetime(self, value):
        return value


class DatabaseWrapper(BaseDatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.features = DatabaseFeatures()
        self.ops = DatabaseOperations()
        self.creation = DatabaseCreation(self)
        self._connection = None
    
    @property
    def connection(self):
        if self._connection is None:
            self._connection = Connection(self.settings_dict["HOST"],
                self.settings_dict["PORT"] or None)
            connection_created.send(sender=self.__class__)
        return self._connection
    
    def _rollback(self):
        # TODO: ???
        pass
