import functools
import re
import uuid


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
    # Regex to capture canonical, hex, integer, and URN formats
    regex = (
        r"([0-9a-f]{32}|"
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|"
        r"urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|"
        r"[0-9]+)"
    )

    def to_python(self, value):
        try:
            if re.match(r"[0-9]+$", value):  # Integer format
                return uuid.UUID(int=int(value))
            return uuid.UUID(value)
        except ValueError:
            return None

    def to_url(self, value):
        return str(value)


class SlugConverter(StringConverter):
    regex = "[-a-zA-Z0-9_]+"


class PathConverter(StringConverter):
    regex = ".+"


DEFAULT_CONVERTERS = {
    "int": IntConverter(),
    "path": PathConverter(),
    "slug": SlugConverter(),
    "str": StringConverter(),
    "uuid": UUIDConverter(),
}


REGISTERED_CONVERTERS = {}


def register_converter(converter, type_name):
    REGISTERED_CONVERTERS[type_name] = converter()
    get_converters.cache_clear()


@functools.cache
def get_converters():
    return {**DEFAULT_CONVERTERS, **REGISTERED_CONVERTERS}


def get_converter(raw_converter):
    return get_converters()[raw_converter]
