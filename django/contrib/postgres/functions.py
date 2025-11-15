import warnings

from django.db.models import DateTimeField, Func
from django.db.models.functions import UUID4
from django.utils.deprecation import RemovedInDjango70Warning


class RandomUUID(UUID4):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Use django.db.models.functions.UUID4 instead.",
            RemovedInDjango70Warning,
        )
        super().__init__(*args, **kwargs)


class TransactionNow(Func):
    template = "CURRENT_TIMESTAMP"
    output_field = DateTimeField()
