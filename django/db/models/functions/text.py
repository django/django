from django.db.models import Func, Transform, Value, fields
from django.db.models.functions import Coalesce


class ConcatPair(Func):
    """
    Concatenate two arguments together. This is used by `Concat` because not
    all backend databases support more than two arguments.
    """
    function = 'CONCAT'

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


class Length(Transform):
    """Return the number of characters in the expression."""
    function = 'LENGTH'
    lookup_name = 'length'
    output_field = fields.IntegerField()

    def as_mysql(self, compiler, connection):
        return super().as_sql(compiler, connection, function='CHAR_LENGTH')


class Lower(Transform):
    function = 'LOWER'
    lookup_name = 'lower'


class Replace(Func):
    function = 'REPLACE'

    def __init__(self, expression, text, replacement=Value(''), **extra):
        super().__init__(expression, text, replacement, **extra)


class StrIndex(Func):
    """
    Return a positive integer corresponding to the 1-indexed position of the
    first occurrence of a substring inside another string, or 0 if the
    substring is not found.
    """
    function = 'INSTR'
    arity = 2
    output_field = fields.IntegerField()

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
