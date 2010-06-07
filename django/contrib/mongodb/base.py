from pymongo import Connection

from django.db.backends import BaseDatabaseWrapper
from django.db.backends.signals import connection_created
from django.contrib.mongodb.creation import DatabaseCreation
from django.utils.importlib import import_module


class DatabaseFeatures(object):
    interprets_empty_strings_as_nulls = False


class DatabaseOperations(object):
    compiler_module = "django.contrib.mongodb.compiler"
    
    def __init__(self, *args, **kwargs):
        self._cache = {}
    
    def max_name_length(self):
        return 254
    
    def value_to_db_datetime(self, value):
        return value

    # TODO: this is copy pasta, fix the abstractions in Ops
    def compiler(self, compiler_name):
        """
        Returns the SQLCompiler class corresponding to the given name,
        in the namespace corresponding to the `compiler_module` attribute
        on this backend.
        """
        if compiler_name not in self._cache:
            self._cache[compiler_name] = getattr(
                import_module(self.compiler_module), compiler_name
            )
        return self._cache[compiler_name]

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
    
    @property
    def db(self):
        return self.connection[self.settings_dict["NAME"]]
    
    def _rollback(self):
        # TODO: ???
        pass
    
    def _commit(self):
        # TODO: ???
        pass
