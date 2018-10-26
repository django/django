from django.db.models import DateTimeField, Func, UUIDField


class RandomUUID(Func):
    template = 'GEN_RANDOM_UUID()'
    output_field = UUIDField()


class TransactionNow(Func):
    template = 'CURRENT_TIMESTAMP'
    output_field = DateTimeField()


class ToJsonb(Func):
    function = 'to_jsonb'


class JsonbCast(Func):
    template = '%(function)s(%(expressions)s)::jsonb'
    function = 'to_json'
