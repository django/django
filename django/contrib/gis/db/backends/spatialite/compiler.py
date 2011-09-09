from django.db.backends.util import typecast_timestamp
from django.db.models.sql import compiler
from django.db.models.sql.constants import MULTI
from django.contrib.gis.db.models.sql.compiler import GeoSQLCompiler as BaseGeoSQLCompiler

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
    """
    This is overridden for GeoDjango to properly cast date columns, see #16757.
    """
    def results_iter(self):
        offset = len(self.query.extra_select)
        for rows in self.execute_sql(MULTI):
            for row in rows:
                date = typecast_timestamp(str(row[offset]))
                yield date
