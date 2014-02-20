from django.contrib.gis.db.models.sql.compiler import GeoSQLCompiler as BaseGeoSQLCompiler
from django.db.backends.mysql import compiler

SQLCompiler = compiler.SQLCompiler


class GeoSQLCompiler(BaseGeoSQLCompiler, SQLCompiler):
    def resolve_columns(self, row, fields=()):
        """
        Integrate the cases handled both by the base GeoSQLCompiler and the
        main MySQL compiler (converting 0/1 to True/False for boolean fields).

        Refs #15169.

        """
        row = BaseGeoSQLCompiler.resolve_columns(self, row, fields)
        return SQLCompiler.resolve_columns(self, row, fields)


class SQLInsertCompiler(compiler.SQLInsertCompiler, GeoSQLCompiler):
    pass


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, GeoSQLCompiler):
    pass


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, GeoSQLCompiler):
    pass


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, GeoSQLCompiler):
    pass


class SQLDateCompiler(compiler.SQLDateCompiler, GeoSQLCompiler):
    pass


class SQLDateTimeCompiler(compiler.SQLDateTimeCompiler, GeoSQLCompiler):
    pass
