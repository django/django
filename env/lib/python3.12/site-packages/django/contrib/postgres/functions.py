from django.db.models import DateTimeField, Func, UUIDField


class RandomUUID(Func):
    template = "GEN_RANDOM_UUID()"
    output_field = UUIDField()


class TransactionNow(Func):
    template = "CURRENT_TIMESTAMP"
    output_field = DateTimeField()
