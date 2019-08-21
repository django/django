"""Database functions that do comparisons or type conversions."""
from django.db.models.expressions import Func, Value


class Cast(Func):
    """Coerce an expression to a new field type."""
    function = 'CAST'
    template = '%(function)s(%(expressions)s AS %(db_type)s)'

    def __init__(self, expression, output_field):
        super().__init__(expression, output_field=output_field)

    def as_sql(self, compiler, connection, **extra_context):
        extra_context['db_type'] = self.output_field.cast_db_type(connection)
        return super().as_sql(compiler, connection, **extra_context)

    def as_sqlite(self, compiler, connection, **extra_context):
        db_type = self.output_field.db_type(connection)
        if db_type in {'datetime', 'time'}:
            # Use strftime as datetime/time don't keep fractional seconds.
            template = 'strftime(%%s, %(expressions)s)'
            sql, params = super().as_sql(compiler, connection, template=template, **extra_context)
            format_string = '%H:%M:%f' if db_type == 'time' else '%Y-%m-%d %H:%M:%f'
            params.insert(0, format_string)
            return sql, params
        elif db_type == 'date':
            template = 'date(%(expressions)s)'
            return super().as_sql(compiler, connection, template=template, **extra_context)
        return self.as_sql(compiler, connection, **extra_context)

    def as_mysql(self, compiler, connection, **extra_context):
        # MySQL doesn't support explicit cast to float.
        template = '(%(expressions)s + 0.0)' if self.output_field.get_internal_type() == 'FloatField' else None
        return self.as_sql(compiler, connection, template=template, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        # CAST would be valid too, but the :: shortcut syntax is more readable.
        # 'expressions' is wrapped in parentheses in case it's a complex
        # expression.
        return self.as_sql(compiler, connection, template='(%(expressions)s)::%(db_type)s', **extra_context)


class Coalesce(Func):
    """Return, from left to right, the first non-null expression."""
    function = 'COALESCE'

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Coalesce must take at least two expressions')
        super().__init__(*expressions, **extra)

    def as_oracle(self, compiler, connection, **extra_context):
        # Oracle prohibits mixing TextField (NCLOB) and CharField (NVARCHAR2),
        # so convert all fields to NCLOB when that type is expected.
        if self.output_field.get_internal_type() == 'TextField':
            clone = self.copy()
            clone.set_source_expressions([
                Func(expression, function='TO_NCLOB') for expression in self.get_source_expressions()
            ])
            return super(Coalesce, clone).as_sql(compiler, connection, **extra_context)
        return self.as_sql(compiler, connection, **extra_context)


class Greatest(Func):
    """
    Return the maximum expression.

    If any expression is null the return value is database-specific:
    On PostgreSQL, the maximum not-null expression is returned.
    On MySQL, Oracle, and SQLite, if any expression is null, null is returned.
    """
    function = 'GREATEST'

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Greatest must take at least two expressions')
        super().__init__(*expressions, **extra)

    def as_sqlite(self, compiler, connection, **extra_context):
        """Use the MAX function on SQLite."""
        return super().as_sqlite(compiler, connection, function='MAX', **extra_context)


class Least(Func):
    """
    Return the minimum expression.

    If any expression is null the return value is database-specific:
    On PostgreSQL, return the minimum not-null expression.
    On MySQL, Oracle, and SQLite, if any expression is null, return null.
    """
    function = 'LEAST'

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Least must take at least two expressions')
        super().__init__(*expressions, **extra)

    def as_sqlite(self, compiler, connection, **extra_context):
        """Use the MIN function on SQLite."""
        return super().as_sqlite(compiler, connection, function='MIN', **extra_context)


class NullIf(Func):
    function = 'NULLIF'
    arity = 2

    def as_oracle(self, compiler, connection, **extra_context):
        expression1 = self.get_source_expressions()[0]
        if isinstance(expression1, Value) and expression1.value is None:
            raise ValueError('Oracle does not allow Value(None) for expression1.')
        return super().as_sql(compiler, connection, **extra_context)
