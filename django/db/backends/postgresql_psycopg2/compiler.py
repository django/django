from django.db.models.sql import compiler

SQLCompiler = compiler.SQLCompiler
SQLDeleteCompiler = compiler.SQLDeleteCompiler
SQLUpdateCompiler = compiler.SQLUpdateCompiler
SQLAggregateCompiler = compiler.SQLAggregateCompiler


class SQLInsertCompiler(compiler.SQLInsertCompiler):
    def as_sql(self):
        """
        Creates the SQL for this query. Returns the SQL string and list
        of parameters.  This is overridden from the original Insert Query class
        to handle the additional SQL Postgres requires to return
        IDs from bulk insert statements.
        """
        if self.return_id and self.connection.features.can_return_ids_from_bulk_insert and \
                (not any(hasattr(field, "get_placeholder") for field in self.query.fields)) and \
                self.connection.features.has_bulk_insert:

            # We don't need quote_name_unless_alias() here, since these are all
            # going to be column names (so we can avoid the extra overhead).
            qn = self.connection.ops.quote_name
            opts = self.query.get_meta()
            result = ['INSERT INTO %s' % qn(opts.db_table)]

            has_fields = bool(self.query.fields)
            fields = self.query.fields if has_fields else [opts.pk]
            result.append('(%s)' % ', '.join(qn(f.column) for f in fields))

            if has_fields:
                params = values = [
                    [
                        f.get_db_prep_save(
                            getattr(obj, f.attname) if self.query.raw else f.pre_save(obj, True),
                            connection=self.connection
                        ) for f in fields
                    ]
                    for obj in self.query.objs
                ]
            else:
                values = [[self.connection.ops.pk_default_value()] for _ in self.query.objs]
                params = [[]]
                fields = [None]

            placeholders = [
                [self.placeholder(field, v) for field, v in zip(fields, val)]
                for val in values
            ]

            result.append(self.connection.ops.bulk_insert_sql(fields, len(values), placeholders=placeholders))

            r_fmt, r_params = self.connection.ops.return_insert_id()
            if r_fmt:
                col = "%s.%s" % (qn(opts.db_table), qn(opts.pk.column))
                result.append(r_fmt % col)
                params += r_params
            return [(" ".join(result), tuple(v for val in values for v in val))]

        else:
            return super(SQLInsertCompiler, self).as_sql()
