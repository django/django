from django.apps import AppConfig
from django.db import connections


class BaseAppConfig(AppConfig):
    name = "apps.query_performing_app"
    database = "default"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_results = []

    def ready(self):
        self.query_results = []
        self._perform_query()

    def _perform_query(self):
        raise NotImplementedError


class ModelQueryAppConfig(BaseAppConfig):
    def _perform_query(self):
        from ..models import TotallyNormal

        queryset = TotallyNormal.objects.using(self.database)
        queryset.update_or_create(name="new name")
        self.query_results = list(queryset.values_list("name"))


class QueryDefaultDatabaseModelAppConfig(ModelQueryAppConfig):
    database = "default"


class QueryOtherDatabaseModelAppConfig(ModelQueryAppConfig):
    database = "other"


class CursorQueryAppConfig(BaseAppConfig):
    def _perform_query(self):
        connection = connections[self.database]
        with connection.cursor() as cursor:
            cursor.execute("SELECT 42" + connection.features.bare_select_suffix)
            self.query_results = cursor.fetchall()


class QueryDefaultDatabaseCursorAppConfig(CursorQueryAppConfig):
    database = "default"


class QueryOtherDatabaseCursorAppConfig(CursorQueryAppConfig):
    database = "other"


class CursorQueryManyAppConfig(BaseAppConfig):
    def _perform_query(self):
        from ..models import TotallyNormal

        connection = connections[self.database]
        table_meta = TotallyNormal._meta
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO %s (%s) VALUES(%%s)"
                % (
                    connection.introspection.identifier_converter(table_meta.db_table),
                    connection.ops.quote_name(table_meta.get_field("name").column),
                ),
                [("test name 1",), ("test name 2",)],
            )
            self.query_results = []


class QueryDefaultDatabaseCursorManyAppConfig(CursorQueryManyAppConfig):
    database = "default"


class QueryOtherDatabaseCursorManyAppConfig(CursorQueryManyAppConfig):
    database = "other"


class StoredProcedureQueryAppConfig(BaseAppConfig):
    def _perform_query(self):
        with connections[self.database].cursor() as cursor:
            cursor.callproc("test_procedure")
            self.query_results = []


class QueryDefaultDatabaseStoredProcedureAppConfig(StoredProcedureQueryAppConfig):
    database = "default"


class QueryOtherDatabaseStoredProcedureAppConfig(StoredProcedureQueryAppConfig):
    database = "other"
