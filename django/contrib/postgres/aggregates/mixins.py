import warnings

from django.core.exceptions import FullResultSet
from django.db.models.expressions import OrderByList
from django.utils.deprecation import RemovedInDjango61Warning


class OrderableAggMixin:
    # RemovedInDjango61Warning: When the deprecation ends, replace with:
    # def __init__(self, *expressions, order_by=(), **extra):
    def __init__(self, *expressions, ordering=(), order_by=(), **extra):
        # RemovedInDjango61Warning.
        if ordering:
            warnings.warn(
                "The ordering argument is deprecated. Use order_by instead.",
                category=RemovedInDjango61Warning,
                stacklevel=2,
            )
            if order_by:
                raise TypeError("Cannot specify both order_by and ordering.")
            order_by = ordering
        if not order_by:
            self.order_by = None
        elif isinstance(order_by, (list, tuple)):
            self.order_by = OrderByList(*order_by)
        else:
            self.order_by = OrderByList(order_by)
        super().__init__(*expressions, **extra)

    def resolve_expression(self, *args, **kwargs):
        if self.order_by is not None:
            self.order_by = self.order_by.resolve_expression(*args, **kwargs)
        return super().resolve_expression(*args, **kwargs)

    def get_source_expressions(self):
        return super().get_source_expressions() + [self.order_by]

    def set_source_expressions(self, exprs):
        *exprs, self.order_by = exprs
        return super().set_source_expressions(exprs)

    def as_sql(self, compiler, connection):
        *source_exprs, filtering_expr, order_by_expr = self.get_source_expressions()

        order_by_sql = ""
        order_by_params = []
        if order_by_expr is not None:
            order_by_sql, order_by_params = compiler.compile(order_by_expr)

        filter_params = []
        if filtering_expr is not None:
            try:
                _, filter_params = compiler.compile(filtering_expr)
            except FullResultSet:
                pass

        source_params = []
        for source_expr in source_exprs:
            source_params += compiler.compile(source_expr)[1]

        sql, _ = super().as_sql(compiler, connection, order_by=order_by_sql)
        return sql, (*source_params, *order_by_params, *filter_params)
