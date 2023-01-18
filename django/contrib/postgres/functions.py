from django.db.models import DateTimeField, Func, UUIDField


class RandomUUID(Func):
    template = "GEN_RANDOM_UUID()"
    output_field = UUIDField()


class Unnest(Func):
    arity = 1
    function = "UNNEST"


class TransactionNow(Func):
    template = "CURRENT_TIMESTAMP"
    output_field = DateTimeField()
