from django.db.models.sql import compiler
# The izip_longest was renamed to zip_longest in py3
try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest


class SQLCompiler(compiler.SQLCompiler):
    def resolve_columns(self, row, fields=()):
        # If this query has limit/offset information, then we expect the
        # first column to be an extra "_RN" column that we need to throw
        # away.
        if self.query.high_mark is not None or self.query.low_mark:
            rn_offset = 1
        else:
            rn_offset = 0
        index_start = rn_offset + len(self.query.extra_select)
        values = [self.query.convert_values(v, None, connection=self.connection)
                  for v in row[rn_offset:index_start]]
        for value, field in zip_longest(row[index_start:], fields):
            values.append(self.query.convert_values(value, field, connection=self.connection))
        return tuple(values)

    def as_sql(self, with_limits=True, with_col_aliases=False):
        """
        Creates the SQL for this query. Returns the SQL string and list
        of parameters.  This is overriden from the original Query class
        to handle the additional SQL Oracle requires to emulate LIMIT
        and OFFSET.

        If 'with_limits' is False, any limit/offset information is not
        included in the query.
        """
        if with_limits and self.query.low_mark == self.query.high_mark:
            return '', ()

        # The `do_offset` flag indicates whether we need to construct
        # the SQL needed to use limit/offset with Oracle.
        do_offset = with_limits and (self.query.high_mark is not None
                                     or self.query.low_mark)
        if not do_offset:
            sql, params = super(SQLCompiler, self).as_sql(with_limits=False,
                    with_col_aliases=with_col_aliases)
        else:
            sql, params = super(SQLCompiler, self).as_sql(with_limits=False,
                                                    with_col_aliases=True)

            # Wrap the base query in an outer SELECT * with boundaries on
            # the "_RN" column.  This is the canonical way to emulate LIMIT
            # and OFFSET on Oracle.
            high_where = ''
            if self.query.high_mark is not None:
                high_where = 'WHERE ROWNUM <= %d' % (self.query.high_mark,)
            sql = 'SELECT * FROM (SELECT ROWNUM AS "_RN", "_SUB".* FROM (%s) "_SUB" %s) WHERE "_RN" > %d' % (sql, high_where, self.query.low_mark)

        return sql, params


class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    pass


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    pass


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    pass


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    pass


class SQLDateCompiler(compiler.SQLDateCompiler, SQLCompiler):
    pass


class SQLDateTimeCompiler(compiler.SQLDateTimeCompiler, SQLCompiler):
    pass
