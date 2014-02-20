from django.contrib.gis.db.models.sql.compiler import GeoSQLCompiler as BaseGeoSQLCompiler
from django.db.backends.oracle import compiler

SQLCompiler = compiler.SQLCompiler


class GeoSQLCompiler(BaseGeoSQLCompiler, SQLCompiler):
    pass


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
