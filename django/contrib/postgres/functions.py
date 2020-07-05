from django.db.models import DateTimeField, Func, UUIDField
from django.db.models.fields import CharField


class JSONBSet(Func):
    """
    Update the value of a JSONField for a specific key.
    Works with nested JSON fields as well.
    """
    function = 'JSONB_SET'
    arity = 4
    output_field = CharField()


class RandomUUID(Func):
    template = 'GEN_RANDOM_UUID()'
    output_field = UUIDField()


class TransactionNow(Func):
    template = 'CURRENT_TIMESTAMP'
    output_field = DateTimeField()
