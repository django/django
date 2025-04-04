import warnings

from django.utils.deprecation import RemovedInDjango61Warning


# RemovedInDjango61Warning.
class _DeprecatedOrdering:
    def __init__(self, *expressions, ordering=(), order_by=(), **extra):
        if ordering:
            warnings.warn(
                "The ordering argument is deprecated. Use order_by instead.",
                category=RemovedInDjango61Warning,
                stacklevel=2,
            )
            if order_by:
                raise TypeError("Cannot specify both order_by and ordering.")
            order_by = ordering

        super().__init__(*expressions, order_by=order_by, **extra)


# RemovedInDjango61Warning: When the deprecation ends, replace with:
# class OrderableAggMixin:
class OrderableAggMixin(_DeprecatedOrdering):
    allow_order_by = True

    def __init_subclass__(cls, /, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
