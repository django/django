import uuid
from functools import lru_cache

from django.utils.http import base36_to_int, int_to_base36


class IntConverter:
    regex = '[0-9]+'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return str(value)


class Base36Converter:
    regex = '[0-9a-z]+'

    def to_python(self, value):
        return base36_to_int(value)

    def to_url(self, value):
        if isinstance(value, str):
            return value
        return int_to_base36(value)


class StringConverter:
    regex = '[^/]+'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


class UUIDConverter:
    regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def to_python(self, value):
        return uuid.UUID(value)

    def to_url(self, value):
        return str(value)


class SlugConverter(StringConverter):
    regex = '[-a-zA-Z0-9_]+'


class PathConverter(StringConverter):
    regex = '.+'


DEFAULT_CONVERTERS = {
    'int': IntConverter(),
    'base36': Base36Converter(),
    'path': PathConverter(),
    'slug': SlugConverter(),
    'str': StringConverter(),
    'uuid': UUIDConverter(),
}


REGISTERED_CONVERTERS = {}


def register_converter(converter, type_name):
    REGISTERED_CONVERTERS[type_name] = converter()
    get_converters.cache_clear()


@lru_cache(maxsize=None)
def get_converters():
    return {**DEFAULT_CONVERTERS, **REGISTERED_CONVERTERS}


def get_converter(raw_converter):
    return get_converters()[raw_converter]
