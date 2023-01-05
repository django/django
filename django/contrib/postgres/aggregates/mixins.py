from django.db.models.expressions import OrderByList


class OrderableAggMixin:
    def __init__(self, *expressions, ordering=(), **extra):
        if isinstance(ordering, (list, tuple)):
            self.order_by = OrderByList(*ordering)
        else:
            self.order_by = OrderByList(ordering)
        super().__init__(*expressions, **extra)

    def resolve_expression(self, *args, **kwargs):
        self.order_by = self.order_by.resolve_expression(*args, **kwargs)
        return super().resolve_expression(*args, **kwargs)

    def get_source_expressions(self):
        if self.order_by.source_expressions:
            return super().get_source_expressions() + [self.order_by]
        return super().get_source_expressions()

    def set_source_expressions(self, exprs):
        if isinstance(exprs[-1], OrderByList):
            *exprs, self.order_by = exprs
        return super().set_source_expressions(exprs)

    def as_sql(self, compiler, connection):
        order_by_sql, order_by_params = compiler.compile(self.order_by)
        sql, sql_params = super().as_sql(compiler, connection, ordering=order_by_sql)
        return sql, (*sql_params, *order_by_params)
