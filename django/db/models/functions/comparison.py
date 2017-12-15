"""Database functions that do comparisons or type conversions."""
from django.db.models import Func


class Cast(Func):
    """Coerce an expression to a new field type."""
    function = 'CAST'
    template = '%(function)s(%(expressions)s AS %(db_type)s)'

    def __init__(self, expression, output_field):
        super().__init__(expression, output_field=output_field)

    def as_sql(self, compiler, connection, **extra_context):
        extra_context['db_type'] = self.output_field.cast_db_type(connection)
        return super().as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection):
        # CAST would be valid too, but the :: shortcut syntax is more readable.
        return self.as_sql(compiler, connection, template='%(expressions)s::%(db_type)s')


class Coalesce(Func):
    """Return, from left to right, the first non-null expression."""
    function = 'COALESCE'

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Coalesce must take at least two expressions')
        super().__init__(*expressions, **extra)

    def as_oracle(self, compiler, connection):
        # Oracle prohibits mixing TextField (NCLOB) and CharField (NVARCHAR2),
        # so convert all fields to NCLOB when that type is expected.
        if self.output_field.get_internal_type() == 'TextField':
            class ToNCLOB(Func):
                function = 'TO_NCLOB'

            expressions = [
                ToNCLOB(expression) for expression in self.get_source_expressions()
            ]
            clone = self.copy()
            clone.set_source_expressions(expressions)
            return super(Coalesce, clone).as_sql(compiler, connection)
        return self.as_sql(compiler, connection)


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

    def as_sqlite(self, compiler, connection):
        """Use the MAX function on SQLite."""
        return super().as_sqlite(compiler, connection, function='MAX')


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

    def as_sqlite(self, compiler, connection):
        """Use the MIN function on SQLite."""
        return super().as_sqlite(compiler, connection, function='MIN')
