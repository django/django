from django.db.models import DateTimeField, Func, UUIDField


class RandomUUID(Func):
    template = 'GEN_RANDOM_UUID()'

    def __init__(self, output_field=None, **extra):
        if output_field is None:
            output_field = UUIDField()
        super().__init__(output_field=output_field, **extra)


class TransactionNow(Func):
    template = 'CURRENT_TIMESTAMP'

    def __init__(self, output_field=None, **extra):
        if output_field is None:
            output_field = DateTimeField()
        super().__init__(output_field=output_field, **extra)
