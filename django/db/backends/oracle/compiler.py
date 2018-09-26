from django.db import NotSupportedError
from django.db.models.sql import compiler


class SQLCompiler(compiler.SQLCompiler):
    def as_sql(self, with_limits=True, with_col_aliases=False):
        """
        Create the SQL for this query. Return the SQL string and list of
        parameters. This is overridden from the original Query class to handle
        the restriction in Oracle 12.1 and emulate LIMIT and OFFSET with
        a subquery.

        If 'with_limits' is False, any limit/offset information is not included
        in the query.
        """
        # Whether the query must be constructed using limit/offset.
        do_offset = with_limits and (self.query.high_mark is not None or self.query.low_mark)
        if not do_offset:
            sql, params = super().as_sql(with_limits=False, with_col_aliases=with_col_aliases)
        elif not self.connection.features.supports_select_for_update_with_limit and self.query.select_for_update:
            raise NotSupportedError(
                'LIMIT/OFFSET is not supported with select_for_update on this '
                'database backend.'
            )
        else:
            sql, params = super().as_sql(with_limits=False, with_col_aliases=True)
            # Wrap the base query in an outer SELECT * with boundaries on
            # the "_RN" column. This is the canonical way to emulate LIMIT
            # and OFFSET on Oracle.
            high_where = ''
            if self.query.high_mark is not None:
                high_where = 'WHERE ROWNUM <= %d' % (self.query.high_mark,)

            if self.query.low_mark:
                sql = (
                    'SELECT * FROM (SELECT "_SUB".*, ROWNUM AS "_RN" FROM (%s) '
                    '"_SUB" %s) WHERE "_RN" > %d' % (sql, high_where, self.query.low_mark)
                )
            else:
                # Simplify the query to support subqueries if there's no offset.
                sql = (
                    'SELECT * FROM (SELECT "_SUB".* FROM (%s) "_SUB" %s)' % (sql, high_where)
                )
        return sql, params


class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    pass


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    pass


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    pass


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    pass
