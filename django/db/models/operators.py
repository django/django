from django.core.exceptions import FieldError
from django.db.models.expressions import CombinedExpression
from django.db.models.fields import (
    CharField, DateField, DateTimeField, DurationField, TextField, TimeField,
)
from django.db.models.functions import ConcatPair

# Don't export anything, the only purpose of this module is to register
# dispatch expressions
__all__ = []


@CombinedExpression.dispatch(
    CombinedExpression.ADD,
    (CharField, TextField),
    (CharField, TextField),
)
class TextAddition(ConcatPair):
    def __init__(self, lhs, connector, rhs, output_field):
        super().__init__(lhs, rhs, output_field=output_field)

@CombinedExpression.dispatch(
    CombinedExpression.ANY, (DurationField, DateTimeField, DateField, TimeField), DurationField)
class DurationExpression(CombinedExpression):
    def as_sql(self, compiler, connection):
        def compile(side):
            try:
                output = side.output_field
            except FieldError:
                pass
            else:
                if output.get_internal_type() == 'DurationField':
                    sql, params = compiler.compile(side)
                    return connection.ops.format_for_duration_arithmetic(sql), params
            return compiler.compile(side)

        if not connection.features.has_native_duration_field:
            connection.ops.check_expression_support(self)
            return self._as_sql(
                compiler, connection, compile=compile,
                combine_expression=connection.ops.combine_duration_expression)

        return self._as_sql(compiler, connection)