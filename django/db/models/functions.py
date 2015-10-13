"""
Classes that represent database functions.
"""
from django.db.models import (
    DateTimeField, Func, IntegerField, Transform, Value,
)


class Coalesce(Func):
    """
    Chooses, from left to right, the first non-null expression and returns it.
    """
    function = 'COALESCE'

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Coalesce must take at least two expressions')
        super(Coalesce, self).__init__(*expressions, **extra)

    def as_oracle(self, compiler, connection):
        # we can't mix TextField (NCLOB) and CharField (NVARCHAR), so convert
        # all fields to NCLOB when we expect NCLOB
        if self.output_field.get_internal_type() == 'TextField':
            class ToNCLOB(Func):
                function = 'TO_NCLOB'

            expressions = [
                ToNCLOB(expression) for expression in self.get_source_expressions()]
            self.set_source_expressions(expressions)
        return super(Coalesce, self).as_sql(compiler, connection)


class ConcatPair(Func):
    """
    A helper class that concatenates two arguments together. This is used
    by `Concat` because not all backend databases support more than two
    arguments.
    """
    function = 'CONCAT'

    def __init__(self, left, right, **extra):
        super(ConcatPair, self).__init__(left, right, **extra)

    def as_sqlite(self, compiler, connection):
        coalesced = self.coalesce()
        coalesced.arg_joiner = ' || '
        coalesced.template = '%(expressions)s'
        return super(ConcatPair, coalesced).as_sql(compiler, connection)

    def as_mysql(self, compiler, connection):
        # Use CONCAT_WS with an empty separator so that NULLs are ignored.
        self.function = 'CONCAT_WS'
        self.template = "%(function)s('', %(expressions)s)"
        return super(ConcatPair, self).as_sql(compiler, connection)

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
    Concatenates text fields together. Backends that result in an entire
    null expression when any arguments are null will wrap each argument in
    coalesce functions to ensure we always get a non-null result.
    """
    function = None
    template = "%(expressions)s"

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Concat must take at least two expressions')
        paired = self._paired(expressions)
        super(Concat, self).__init__(paired, **extra)

    def _paired(self, expressions):
        # wrap pairs of expressions in successive concat functions
        # exp = [a, b, c, d]
        # -> ConcatPair(a, ConcatPair(b, ConcatPair(c, d))))
        if len(expressions) == 2:
            return ConcatPair(*expressions)
        return ConcatPair(expressions[0], self._paired(expressions[1:]))


class Greatest(Func):
    """
    Chooses the maximum expression and returns it.

    If any expression is null the return value is database-specific:
    On Postgres, the maximum not-null expression is returned.
    On MySQL, Oracle, and SQLite, if any expression is null, null is returned.
    """
    function = 'GREATEST'

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Greatest must take at least two expressions')
        super(Greatest, self).__init__(*expressions, **extra)

    def as_sqlite(self, compiler, connection):
        """Use the MAX function on SQLite."""
        return super(Greatest, self).as_sql(compiler, connection, function='MAX')


class Least(Func):
    """
    Chooses the minimum expression and returns it.

    If any expression is null the return value is database-specific:
    On Postgres, the minimum not-null expression is returned.
    On MySQL, Oracle, and SQLite, if any expression is null, null is returned.
    """
    function = 'LEAST'

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Least must take at least two expressions')
        super(Least, self).__init__(*expressions, **extra)

    def as_sqlite(self, compiler, connection):
        """Use the MIN function on SQLite."""
        return super(Least, self).as_sql(compiler, connection, function='MIN')


class Length(Transform):
    """Returns the number of characters in the expression"""
    function = 'LENGTH'
    lookup_name = 'length'

    def __init__(self, expression, **extra):
        output_field = extra.pop('output_field', IntegerField())
        super(Length, self).__init__(expression, output_field=output_field, **extra)

    def as_mysql(self, compiler, connection):
        self.function = 'CHAR_LENGTH'
        return super(Length, self).as_sql(compiler, connection)


class Lower(Transform):
    function = 'LOWER'
    lookup_name = 'lower'

    def __init__(self, expression, **extra):
        super(Lower, self).__init__(expression, **extra)


class Now(Func):
    template = 'CURRENT_TIMESTAMP'

    def __init__(self, output_field=None, **extra):
        if output_field is None:
            output_field = DateTimeField()
        super(Now, self).__init__(output_field=output_field, **extra)

    def as_postgresql(self, compiler, connection):
        # Postgres' CURRENT_TIMESTAMP means "the time at the start of the
        # transaction". We use STATEMENT_TIMESTAMP to be cross-compatible with
        # other databases.
        self.template = 'STATEMENT_TIMESTAMP()'
        return self.as_sql(compiler, connection)


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
            pos = Value(pos)
        expressions = [expression, pos]
        if length is not None:
            if not hasattr(length, 'resolve_expression'):
                length = Value(length)
            expressions.append(length)
        super(Substr, self).__init__(*expressions, **extra)

    def as_sqlite(self, compiler, connection):
        self.function = 'SUBSTR'
        return super(Substr, self).as_sql(compiler, connection)

    def as_oracle(self, compiler, connection):
        self.function = 'SUBSTR'
        return super(Substr, self).as_sql(compiler, connection)


class Upper(Transform):
    function = 'UPPER'
    lookup_name = 'upper'

    def __init__(self, expression, **extra):
        super(Upper, self).__init__(expression, **extra)
