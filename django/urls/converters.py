import datetime
import functools
import uuid


class DateConverter:
    regex = r"\d{4}-\d{2}-\d{2}"

    def to_python(self, value: str) -> datetime.date:
        return datetime.date.fromisoformat(value)

    def to_url(self, value: datetime.date) -> str:
        return value.isoformat()


class IntConverter:
    regex = "[0-9]+"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return str(value)


class StringConverter:
    regex = "[^/]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


class UUIDConverter:
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def to_python(self, value):
        return uuid.UUID(value)

    def to_url(self, value):
        return str(value)


class SlugConverter(StringConverter):
    regex = "[-a-zA-Z0-9_]+"


class PathConverter(StringConverter):
    regex = ".+"


DEFAULT_CONVERTERS = {
    "date": DateConverter(),
    "int": IntConverter(),
    "path": PathConverter(),
    "slug": SlugConverter(),
    "str": StringConverter(),
    "uuid": UUIDConverter(),
}


REGISTERED_CONVERTERS = {}


def register_converter(converter, type_name):
    if type_name in REGISTERED_CONVERTERS or type_name in DEFAULT_CONVERTERS:
        raise ValueError(f"Converter {type_name!r} is already registered.")
    REGISTERED_CONVERTERS[type_name] = converter()
    get_converters.cache_clear()

    from django.urls.resolvers import _route_to_regex

    _route_to_regex.cache_clear()


@functools.cache
def get_converters():
    return {**DEFAULT_CONVERTERS, **REGISTERED_CONVERTERS}
