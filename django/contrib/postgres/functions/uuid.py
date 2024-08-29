from django.db.models import Func, UUIDField


class RandomUUID(Func):
    template = "GEN_RANDOM_UUID()"
    output_field = UUIDField()
