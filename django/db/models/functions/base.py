"""
Classes that represent database functions.
"""
from django.db.models import Func, Transform, Value, fields


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
        # we can't mix TextField (NCLOB) and CharField (NVARCHAR), so convert
        # all fields to NCLOB when we expect NCLOB
        if self.output_field.get_internal_type() == 'TextField':
            class ToNCLOB(Func):
                function = 'TO_NCLOB'

            expressions = [
                ToNCLOB(expression) for expression in self.get_source_expressions()]
            clone = self.copy()
            clone.set_source_expressions(expressions)
            return super(Coalesce, clone).as_sql(compiler, connection)
        return self.as_sql(compiler, connection)


class ConcatPair(Func):
    """
    Concatenate two arguments together. This is used by `Concat` because not
    all backend databases support more than two arguments.
    """
    function = 'CONCAT'

    def __init__(self, left, right, **extra):
        super().__init__(left, right, **extra)

    def as_sqlite(self, compiler, connection):
        coalesced = self.coalesce()
        return super(ConcatPair, coalesced).as_sql(
            compiler, connection, template='%(expressions)s', arg_joiner=' || '
        )

    def as_mysql(self, compiler, connection):
        # Use CONCAT_WS with an empty separator so that NULLs are ignored.
        return super().as_sql(
            compiler, connection, function='CONCAT_WS', template="%(function)s('', %(expressions)s)"
        )

    def coalesce(self):
        # null on either side results in null for expression, wrap with coalesce
        c = self.copy()
        expressions = [
            Coalesce(expression, Value('')) for expression in c.get_source_expressions()
        ]
        c.set_source_expressions(expressions)
        return c


class Concat(Func):
    """
    Concatenate text fields together. Backends that result in an entire
    null expression when any arguments are null will wrap each argument in
    coalesce functions to ensure a non-null result.
    """
    function = None
    template = "%(expressions)s"

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Concat must take at least two expressions')
        paired = self._paired(expressions)
        super().__init__(paired, **extra)

    def _paired(self, expressions):
        # wrap pairs of expressions in successive concat functions
        # exp = [a, b, c, d]
        # -> ConcatPair(a, ConcatPair(b, ConcatPair(c, d))))
        if len(expressions) == 2:
            return ConcatPair(*expressions)
        return ConcatPair(expressions[0], self._paired(expressions[1:]))


class Greatest(Func):
    """
    Return the maximum expression.

    If any expression is null the return value is database-specific:
    On Postgres, the maximum not-null expression is returned.
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
    On Postgres, return the minimum not-null expression.
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


class Length(Transform):
    """Return the number of characters in the expression."""
    function = 'LENGTH'
    lookup_name = 'length'

    def __init__(self, expression, *, output_field=None, **extra):
        super().__init__(expression, output_field=output_field or fields.IntegerField(), **extra)

    def as_mysql(self, compiler, connection):
        return super().as_sql(compiler, connection, function='CHAR_LENGTH')


class Lower(Transform):
    function = 'LOWER'
    lookup_name = 'lower'


class Now(Func):
    template = 'CURRENT_TIMESTAMP'

    def __init__(self, output_field=None, **extra):
        if output_field is None:
            output_field = fields.DateTimeField()
        super().__init__(output_field=output_field, **extra)

    def as_postgresql(self, compiler, connection):
        # Postgres' CURRENT_TIMESTAMP means "the time at the start of the
        # transaction". We use STATEMENT_TIMESTAMP to be cross-compatible with
        # other databases.
        return self.as_sql(compiler, connection, template='STATEMENT_TIMESTAMP()')


class StrIndex(Func):
    """
    Return a positive integer corresponding to the 1-indexed position of the
    first occurrence of a substring inside another string, or 0 if the
    substring is not found.
    """
    function = 'INSTR'
    arity = 2

    def __init__(self, string, substring, **extra):
        """
        string: the name of a field, or an expression returning a string
        substring: the name of a field, or an expression returning a string
        """
        super().__init__(string, substring, output_field=fields.IntegerField(), **extra)

    def as_postgresql(self, compiler, connection):
        return super().as_sql(compiler, connection, function='STRPOS')


class Substr(Func):
    function = 'SUBSTRING'

    def __init__(self, expression, pos, length=None, **extra):
        """
        expression: the name of a field, or an expression returning a string
        pos: an integer > 0, or an expression returning an integer
        length: an optional number of characters to return
        """
        if not hasattr(pos, 'resolve_expression'):
            if pos < 1:
                raise ValueError("'pos' must be greater than 0")
        expressions = [expression, pos]
        if length is not None:
            expressions.append(length)
        super().__init__(*expressions, **extra)

    def as_sqlite(self, compiler, connection):
        return super().as_sql(compiler, connection, function='SUBSTR')

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection, function='SUBSTR')


class Upper(Transform):
    function = 'UPPER'
    lookup_name = 'upper'
