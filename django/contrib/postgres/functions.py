from django.db.models import DateTimeField, Func, UUIDField, IntegerField


class RandomUUID(Func):
    template = "GEN_RANDOM_UUID()"
    output_field = UUIDField()


class TransactionNow(Func):
    template = "CURRENT_TIMESTAMP"
    output_field = DateTimeField()


class NumNonNulls(Func):
    function = "num_nonnulls"
    output_field = IntegerField()


