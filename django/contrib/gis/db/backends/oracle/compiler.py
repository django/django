from django.contrib.gis.db.models.sql.compiler import GeoSQLCompiler as BaseGeoSQLCompiler
from django.db.backends.oracle import compiler

SQLCompiler = compiler.SQLCompiler

class GeoSQLCompiler(BaseGeoSQLCompiler, SQLCompiler):
    pass

class SQLInsertCompiler(compiler.SQLInsertCompiler, GeoSQLCompiler):
    def placeholder(self, field, val):
        if field is None:
            # A field value of None means the value is raw.
            return val
        elif hasattr(field, 'get_placeholder'):
            # Some fields (e.g. geo fields) need special munging before
            # they can be inserted.
            ph = field.get_placeholder(val, self.connection)
            if ph == 'NULL':
                # If the placeholder returned is 'NULL', then we need to
                # to remove None from the Query parameters. Specifically,
                # cx_Oracle will assume a CHAR type when a placeholder ('%s')
                # is used for columns of MDSYS.SDO_GEOMETRY.  Thus, we use
                # 'NULL' for the value, and remove None from the query params.
                # See also #10888.
                param_idx = self.query.columns.index(field.column)
                params = list(self.query.params)
                params.pop(param_idx)
                self.query.params = tuple(params)
            return ph
        else:
            # Return the common case for the placeholder
            return '%s'

class SQLDeleteCompiler(compiler.SQLDeleteCompiler, GeoSQLCompiler):
    pass

class SQLUpdateCompiler(compiler.SQLUpdateCompiler, GeoSQLCompiler):
    pass

class SQLAggregateCompiler(compiler.SQLAggregateCompiler, GeoSQLCompiler):
    pass

class SQLDateCompiler(compiler.SQLDateCompiler, GeoSQLCompiler):
    pass
