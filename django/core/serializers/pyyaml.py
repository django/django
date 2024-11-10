"""
YAML serializer.

Requires PyYaml (https://pyyaml.org/), but that's checked for in __init__.
"""

import collections
import datetime
import decimal

import yaml

from django.core.serializers.base import DeserializationError
from django.core.serializers.python import Deserializer as PythonDeserializer
from django.core.serializers.python import Serializer as PythonSerializer

# Use the C (faster) implementation if possible
try:
    from yaml import CSafeDumper as SafeDumper
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeDumper, SafeLoader


class DjangoSafeDumper(SafeDumper):
    def represent_decimal(self, data):
        return self.represent_scalar("tag:yaml.org,2002:str", str(data))

    def represent_ordered_dict(self, data):
        return self.represent_mapping("tag:yaml.org,2002:map", data.items())


DjangoSafeDumper.add_representer(decimal.Decimal, DjangoSafeDumper.represent_decimal)
DjangoSafeDumper.add_representer(
    collections.OrderedDict, DjangoSafeDumper.represent_ordered_dict
)
# Workaround to represent dictionaries in insertion order.
# See https://github.com/yaml/pyyaml/pull/143.
DjangoSafeDumper.add_representer(dict, DjangoSafeDumper.represent_ordered_dict)


class Serializer(PythonSerializer):
    """Convert a queryset to YAML."""

    internal_use_only = False

    def _value_from_field(self, obj, field):
        # A nasty special case: base YAML doesn't support serialization of time
        # types (as opposed to dates or datetimes, which it does support). Since
        # we want to use the "safe" serializer for better interoperability, we
        # need to do something with those pesky times. Converting 'em to strings
        # isn't perfect, but it's better than a "!!python/time" type which would
        # halt deserialization under any other language.
        value = super()._value_from_field(obj, field)
        if isinstance(value, datetime.time):
            value = str(value)
        return value

    def end_serialization(self):
        self.options.setdefault("allow_unicode", True)
        yaml.dump(self.objects, self.stream, Dumper=DjangoSafeDumper, **self.options)

    def getvalue(self):
        # Grandparent super
        return super(PythonSerializer, self).getvalue()


class Deserializer(PythonDeserializer):
    """Deserialize a stream or string of YAML data."""

    def __init__(self, stream_or_string, **options):
        stream = stream_or_string
        if isinstance(stream_or_string, bytes):
            stream = stream_or_string.decode()
        try:
            objects = yaml.load(stream, Loader=SafeLoader)
        except Exception as exc:
            raise DeserializationError() from exc
        super().__init__(objects, **options)

    def _handle_object(self, obj):
        try:
            yield from super()._handle_object(obj)
        except (GeneratorExit, DeserializationError):
            raise
        except Exception as exc:
            raise DeserializationError(f"Error deserializing object: {exc}") from exc
