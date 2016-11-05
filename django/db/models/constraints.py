from django.db.models.sql.query import Query

__all__ = ['CheckConstraint']


class CheckConstraint:
    def __init__(self, constraint, name):
        self.constraint = constraint
        self.name = name

    def constraint_sql(self, model, schema_editor):
        query = Query(model)
        where = query.build_where(self.constraint)
        connection = schema_editor.connection
        compiler = connection.ops.compiler('SQLCompiler')(query, connection, 'default')
        sql, params = where.as_sql(compiler, connection)
        params = tuple(schema_editor.quote_value(p) for p in params)
        return schema_editor.sql_check % {
            'name': schema_editor.quote_name(self.name),
            'check': sql % params,
        }

    def create_sql(self, model, schema_editor):
        sql = self.constraint_sql(model, schema_editor)
        return schema_editor.sql_create_check % {
            'table': schema_editor.quote_name(model._meta.db_table),
            'check': sql,
        }

    def remove_sql(self, model, schema_editor):
        quote_name = schema_editor.quote_name
        return schema_editor.sql_delete_check % {
            'table': quote_name(model._meta.db_table),
            'name': quote_name(self.name),
        }

    def __repr__(self):
        return "<%s: constraint='%s' name='%s'>" % (self.__class__.__name__, self.constraint, self.name)

    def __eq__(self, other):
        return (
            isinstance(other, CheckConstraint) and
            self.name == other.name and
            self.constraint == other.constraint
        )

    def deconstruct(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        path = path.replace('django.db.models.constraints', 'django.db.models')
        return (path, (), {'constraint': self.constraint, 'name': self.name})

    def clone(self):
        _, args, kwargs = self.deconstruct()
        return self.__class__(*args, **kwargs)
