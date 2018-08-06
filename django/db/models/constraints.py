from django.db.models.sql.query import Query

__all__ = ['CheckConstraint', 'UniqueConstraint']


class BaseConstraint:
    def __init__(self, name):
        self.name = name

    def constraint_sql(self, model, schema_editor):
        raise NotImplementedError('This method must be implemented by a subclass.')

    def full_constraint_sql(self, model, schema_editor):
        return schema_editor.sql_constraint % {
            'name': schema_editor.quote_name(self.name),
            'constraint': self.constraint_sql(model, schema_editor),
        }

    def create_sql(self, model, schema_editor):
        sql = self.full_constraint_sql(model, schema_editor)
        return schema_editor.sql_create_constraint % {
            'table': schema_editor.quote_name(model._meta.db_table),
            'constraint': sql,
        }

    def remove_sql(self, model, schema_editor):
        quote_name = schema_editor.quote_name
        return schema_editor.sql_delete_constraint % {
            'table': quote_name(model._meta.db_table),
            'name': quote_name(self.name),
        }

    def deconstruct(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        path = path.replace('django.db.models.constraints', 'django.db.models')
        return (path, (), {'name': self.name})

    def clone(self):
        _, args, kwargs = self.deconstruct()
        return self.__class__(*args, **kwargs)


class CheckConstraint(BaseConstraint):
    def __init__(self, *, check, name):
        self.check = check
        super().__init__(name)

    def constraint_sql(self, model, schema_editor):
        query = Query(model)
        where = query.build_where(self.check)
        connection = schema_editor.connection
        compiler = connection.ops.compiler('SQLCompiler')(query, connection, 'default')
        sql, params = where.as_sql(compiler, connection)
        params = tuple(schema_editor.quote_value(p) for p in params)
        return schema_editor.sql_check_constraint % {'check': sql % params}

    def __repr__(self):
        return "<%s: check='%s' name=%r>" % (self.__class__.__name__, self.check, self.name)

    def __eq__(self, other):
        return (
            isinstance(other, CheckConstraint) and
            self.name == other.name and
            self.check == other.check
        )

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs['check'] = self.check
        return path, args, kwargs


class UniqueConstraint(BaseConstraint):
    def __init__(self, *, fields, name):
        if not fields:
            raise ValueError('At least one field is required to define a unique constraint.')
        self.fields = tuple(fields)
        super().__init__(name)

    def constraint_sql(self, model, schema_editor):
        columns = (
            model._meta.get_field(field_name).column
            for field_name in self.fields
        )
        return schema_editor.sql_unique_constraint % {
            'columns': ', '.join(map(schema_editor.quote_name, columns)),
        }

    def create_sql(self, model, schema_editor):
        columns = [model._meta.get_field(field_name).column for field_name in self.fields]
        return schema_editor._create_unique_sql(model, columns, self.name)

    def __repr__(self):
        return '<%s: fields=%r name=%r>' % (self.__class__.__name__, self.fields, self.name)

    def __eq__(self, other):
        return (
            isinstance(other, UniqueConstraint) and
            self.name == other.name and
            self.fields == other.fields
        )

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs['fields'] = self.fields
        return path, args, kwargs
