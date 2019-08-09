from django.db.models.expressions import Exists
from django.db.models.sql import compiler


class SQLCompiler(compiler.SQLCompiler):
    @staticmethod
    def _wrap_exists(expr, sql, params):
        # Oracle doesn't allow EXISTS() in the SELECT clauses unless it's
        # wrapped with a CASE WHEN expression. This is done here and not in
        # Exists.as_oracle because the latter is not aware of which part of
        # the query it's compiled for.
        if isinstance(expr, Exists):
            sql = 'CASE WHEN %s THEN 1 ELSE 0 END' % sql
        return sql, params

    def get_select(self):
        select, klass_info, annotation_col_map = super().get_select()
        select = [
            (expr, self._wrap_exists(expr, sql, params), alias)
            for expr, (sql, params), alias in select
        ]
        return select, klass_info, annotation_col_map


SQLInsertCompiler = compiler.SQLInsertCompiler
SQLDeleteCompiler = compiler.SQLDeleteCompiler
SQLUpdateCompiler = compiler.SQLUpdateCompiler
SQLAggregateCompiler = compiler.SQLAggregateCompiler
