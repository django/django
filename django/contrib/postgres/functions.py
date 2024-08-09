from django.db.models import DateTimeField, Func, UUIDField


class RandomUUID(Func):
    """
    Without `pgcrypto` or `uuid-ossp` extensions enabled, available only
    since PostgreSQL 13.

    https://www.postgresql.org/docs/13/functions-uuid.html
    """

    template = "GEN_RANDOM_UUID()"
    output_field = UUIDField()


class TransactionNow(Func):
    template = "CURRENT_TIMESTAMP"
    output_field = DateTimeField()
