from django.db.models.sql.query import Query

__all__ = ['CheckConstraint']


class CheckConstraint:
    def __init__(self, *, check, name):
        self.check = check
        self.name = name

    def constraint_sql(self, model, schema_editor):
        query = Query(model)
        where = query.build_where(self.check)
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
        return "<%s: check='%s' name=%r>" % (self.__class__.__name__, self.check, self.name)

    def __eq__(self, other):
        return (
            isinstance(other, CheckConstraint) and
            self.name == other.name and
            self.check == other.check
        )

    def deconstruct(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        path = path.replace('django.db.models.constraints', 'django.db.models')
        return (path, (), {'check': self.check, 'name': self.name})

    def clone(self):
        _, args, kwargs = self.deconstruct()
        return self.__class__(*args, **kwargs)
