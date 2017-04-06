import copy

from django.core.exceptions import FieldError
from django.db.models import Aggregate, Expression, Q


class FilterMixin:
    def filter(self, **kwargs):
        if not kwargs:
            return self

        return FilterWhere(expression=self, condition=Q(**kwargs))

    def exclude(self, **kwargs):
        if not kwargs:
            return self

        return FilterWhere(expression=self, condition=~Q(**kwargs))


class PostgresAggregate(FilterMixin, Aggregate):
    pass


class FilterWhere(FilterMixin, Expression):
    template = '%(expression)s FILTER (WHERE %(condition)s)'

    def __init__(self, expression, condition, output_field=None):
        if not expression.contains_aggregate:
            raise TypeError('Expression must either be an aggregate function or contain an aggregate function')

        if not hasattr(condition, 'resolve_expression'):
            raise TypeError('Condition must be a class defining resolve_expression')

        super().__init__(output_field=output_field)

        if isinstance(expression, FilterWhere):
            self.condition = Q(expression.condition, condition)
            self.source_expression = expression.source_expression
        else:
            self.source_expression = self._parse_expressions(expression)[0]
            self.condition = condition

        if not getattr(self.source_expression, 'contains_aggregate', False):
            raise FieldError('Window function expressions must be aggregate functions')

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        c = self.copy()
        c.source_expression = self.source_expression.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        c.condition = self.condition.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        return c

    def _resolve_output_field(self):
        if self._output_field is None:
            self._output_field = self.source_expression.output_field

    def copy(self):
        clone = super().copy()
        clone.source_expression = self.source_expression.copy()
        clone.condition = copy.copy(self.condition)
        return clone

    def as_sql(self, compiler, connection):
        connection.ops.check_expression_support(self)
        params = []
        condition_sql, condition_params = compiler.compile(self.condition)
        params.extend(condition_params)
        expr_sql, expr_params = compiler.compile(self.source_expression)
        condition_params.extend(expr_params)

        return self.template % {
            'expression': expr_sql,
            'condition': condition_sql,
        }, params

    def get_source_expressions(self):
        return self.source_expression, self.condition

    def set_source_expressions(self, exprs):
        self.source_expression, self.condition = exprs[0], exprs[1]

    def get_group_by_cols(self):
        return []

    def __str__(self):
        return self.template % {
            'expression': str(self.source_expression),
            'condition': str(self.condition),
        }

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self)
