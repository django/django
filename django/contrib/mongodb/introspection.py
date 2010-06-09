from django.db.backends import BaseDatabaseIntrospection


class DatabaseIntrospection(BaseDatabaseIntrospection):
    def table_names(self):
        return self.connection.db.collection_names()
