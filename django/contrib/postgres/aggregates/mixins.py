from django.db.models.expressions import F, OrderBy


class OrderableAggMixin:

    def __init__(self, expression, ordering=(), **extra):
        if not isinstance(ordering, (list, tuple)):
            ordering = [ordering]
        ordering = ordering or []
        # Transform minus sign prefixed strings into an OrderBy() expression.
        ordering = (
            (OrderBy(F(o[1:]), descending=True) if isinstance(o, str) and o[0] == '-' else o)
            for o in ordering
        )
        super().__init__(expression, **extra)
        self.ordering = self._parse_expressions(*ordering)

    def resolve_expression(self, *args, **kwargs):
        self.ordering = [expr.resolve_expression(*args, **kwargs) for expr in self.ordering]
        return super().resolve_expression(*args, **kwargs)

    def as_sql(self, compiler, connection):
        if self.ordering:
            self.extra['ordering'] = 'ORDER BY ' + ', '.join((
                ordering_element.as_sql(compiler, connection)[0]
                for ordering_element in self.ordering
            ))
        else:
            self.extra['ordering'] = ''
        return super().as_sql(compiler, connection)

    def get_source_expressions(self):
        return self.source_expressions + self.ordering

    def get_source_fields(self):
        # Filter out fields contributed by the ordering expressions as
        # these should not be used to determine which the return type of the
        # expression.
        return [
            e._output_field_or_none
            for e in self.get_source_expressions()[:self._get_ordering_expressions_index()]
        ]

    def _get_ordering_expressions_index(self):
        """Return the index at which the ordering expressions start."""
        source_expressions = self.get_source_expressions()
        return len(source_expressions) - len(self.ordering)
