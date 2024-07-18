import warnings

from django.db.models import Aggregate
from django.utils.deprecation import RemovedInDjango60Warning


class _DeprecatedOrdering:
    def __init__(self, *expressions, ordering=(), **extra):
        if ordering:
            warnings.warn(
                "The ordering argument is deprecated. Use order_by instead.",
                category=RemovedInDjango60Warning,
                stacklevel=1
            )
        super().__init__(*expressions, **extra)


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
