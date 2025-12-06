import warnings

from django.db.models import DateTimeField, Func
from django.db.models.functions import UUID4
from django.utils.deprecation import RemovedInDjango70Warning, django_file_prefixes


class RandomUUID(UUID4):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "RandomUUID is deprecated. Use django.db.models.functions.UUID4 instead.",
            RemovedInDjango70Warning,
            skip_file_prefixes=django_file_prefixes(),
        )
        super().__init__(*args, **kwargs)


class TransactionNow(Func):
    template = "CURRENT_TIMESTAMP"
    output_field = DateTimeField()
