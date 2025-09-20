# RemovedInDjango70Warning: When the deprecation ends, remove completely.
import warnings

from django.utils.deprecation import RemovedInDjango70Warning, django_file_prefixes


# RemovedInDjango70Warning.
class OrderableAggMixin:
    allow_order_by = True

    def __init_subclass__(cls, /, *args, **kwargs):
        warnings.warn(
            "OrderableAggMixin is deprecated. Use Aggregate and allow_order_by "
            "instead.",
            category=RemovedInDjango70Warning,
            skip_file_prefixes=django_file_prefixes(),
        )
        super().__init_subclass__(*args, **kwargs)
