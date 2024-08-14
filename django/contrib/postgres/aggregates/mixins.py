import warnings

from django.utils.deprecation import RemovedInDjango60Warning


class _DeprecatedOrdering:
    def __init__(self, *expressions, ordering=(), order_by=(), **extra):
        if ordering and order_by:
            raise TypeError("order_by and ordering both provided.")

        if ordering:
            warnings.warn(
                "The ordering argument is deprecated. Use order_by instead.",
                category=RemovedInDjango60Warning,
                stacklevel=2,
            )
            order_by = ordering

        super().__init__(*expressions, order_by=order_by, **extra)


class OrderableAggMixin(_DeprecatedOrdering):
    allow_order_by = True

    def __init_subclass__(cls, /, *args, **kwargs):
        warnings.warn(
            "OrderableAggMixin is deprecated. Use Aggregate and allow_order_by "
            "instead.",
            category=RemovedInDjango60Warning,
            stacklevel=1,
        )
        super().__init_subclass__(*args, **kwargs)
