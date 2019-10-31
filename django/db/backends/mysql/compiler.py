from django.db.models.sql import compiler


class SQLCompiler(compiler.SQLCompiler):
    def as_subquery_condition(self, alias, columns, compiler):
        qn = compiler.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        sql, params = self.as_sql()
        return '(%s) IN (%s)' % (', '.join('%s.%s' % (qn(alias), qn2(column)) for column in columns), sql), params


class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    pass


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    def as_sql(self):
        if self.connection.features.update_can_self_select or self.single_alias:
            return super().as_sql()
        # MySQL and MariaDB < 10.3.2 doesn't support deletion with a subquery
        # which is what the default implementation of SQLDeleteCompiler uses
        # when multiple tables are involved. Use the MySQL/MariaDB specific
        # DELETE table FROM table syntax instead to avoid performing the
        # operation in two queries.
        result = [
            'DELETE %s FROM' % self.quote_name_unless_alias(
                self.query.get_initial_alias()
            )
        ]
        from_sql, from_params = self.get_from_clause()
        result.extend(from_sql)
        where, params = self.compile(self.query.where)
        if where:
            result.append('WHERE %s' % where)
        return ' '.join(result), tuple(from_params) + tuple(params)


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    pass


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    pass
