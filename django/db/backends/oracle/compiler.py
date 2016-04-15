from django.db.models.sql import compiler


class SQLCompiler(compiler.SQLCompiler):
    def as_sql(self, with_limits=True, with_col_aliases=False, subquery=False):
        """
        Creates the SQL for this query. Returns the SQL string and list
        of parameters.  This is overridden from the original Query class
        to handle the additional SQL Oracle requires to emulate LIMIT
        and OFFSET.

        If 'with_limits' is False, any limit/offset information is not
        included in the query.
        """
        # The `do_offset` flag indicates whether we need to construct
        # the SQL needed to use limit/offset with Oracle.
        do_offset = with_limits and (self.query.high_mark is not None or self.query.low_mark)
        if not do_offset:
            sql, params = super(SQLCompiler, self).as_sql(
                with_limits=False,
                with_col_aliases=with_col_aliases,
                subquery=subquery,
            )
        else:
            sql, params = super(SQLCompiler, self).as_sql(
                with_limits=False,
                with_col_aliases=True,
                subquery=subquery,
            )
            # Wrap the base query in an outer SELECT * with boundaries on
            # the "_RN" column.  This is the canonical way to emulate LIMIT
            # and OFFSET on Oracle.
            high_where = ''
            if self.query.high_mark is not None:
                high_where = 'WHERE ROWNUM <= %d' % (self.query.high_mark,)
            sql = (
                'SELECT * FROM (SELECT "_SUB".*, ROWNUM AS "_RN" FROM (%s) '
                '"_SUB" %s) WHERE "_RN" > %d' % (sql, high_where, self.query.low_mark)
            )

        return sql, params


class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    def as_sql(self):
        can_bulk = (not self.return_id and self.connection.features.has_bulk_insert)
        if not can_bulk:
            return super(SQLInsertCompiler, self).as_sql()

        result = ["INSERT ALL"]

        fields = self.query.fields
        has_fields = bool(self.query.fields)

        if has_fields:
            value_rows = [
                [self.prepare_value(field, self.pre_save_val(field, obj)) for field in fields]
                for obj in self.query.objs
            ]
        else:
            # An empty object.
            value_rows = [[self.connection.ops.pk_default_value()] for _ in self.query.objs]
            fields = [None]

        placeholder_rows, param_rows = self.assemble_as_sql(fields, value_rows)

        opts = self.query.get_meta()
        qn = self.connection.ops.quote_name
        fields = self.query.fields if has_fields else [opts.pk]
        result.append(self.connection.ops.bulk_insert_sql(fields, placeholder_rows).format(table=qn(opts.db_table)))

        result.append('SELECT * FROM DUAL')

        return [(" ".join(result), tuple(p for ps in param_rows for p in ps))]


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    pass


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    pass


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    pass
