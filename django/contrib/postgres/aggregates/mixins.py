# RemovedInDjango2028Warning: When the deprecation ends, remove completely.
import warnings

from django.utils.deprecation import RemovedInDjango2028Warning


# RemovedInDjango2028Warning.
class OrderableAggMixin:
    allow_order_by = True

    def __init_subclass__(cls, /, *args, **kwargs):
        warnings.warn(
            "OrderableAggMixin is deprecated. Use Aggregate and allow_order_by "
            "instead.",
            category=RemovedInDjango2028Warning,
            stacklevel=1,
        )
        super().__init_subclass__(*args, **kwargs)
