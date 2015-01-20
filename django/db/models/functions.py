"""
Classes that represent database functions.
"""
from django.db.models import IntegerField
from django.db.models.expressions import Func, Value


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
        self.arg_joiner = ' || '
        self.template = '%(expressions)s'
        self.coalesce()
        return super(ConcatPair, self).as_sql(compiler, connection)

    def as_mysql(self, compiler, connection):
        self.coalesce()
        return super(ConcatPair, self).as_sql(compiler, connection)

    def coalesce(self):
        # null on either side results in null for expression, wrap with coalesce
        expressions = [
            Coalesce(expression, Value('')) for expression in self.get_source_expressions()]
        self.set_source_expressions(expressions)


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


class Length(Func):
    """Returns the number of characters in the expression"""
    function = 'LENGTH'

    def __init__(self, expression, **extra):
        output_field = extra.pop('output_field', IntegerField())
        super(Length, self).__init__(expression, output_field=output_field, **extra)

    def as_mysql(self, compiler, connection):
        self.function = 'CHAR_LENGTH'
        return super(Length, self).as_sql(compiler, connection)


class Lower(Func):
    function = 'LOWER'

    def __init__(self, expression, **extra):
        super(Lower, self).__init__(expression, **extra)


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


class Upper(Func):
    function = 'UPPER'

    def __init__(self, expression, **extra):
        super(Upper, self).__init__(expression, **extra)
