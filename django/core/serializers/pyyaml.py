"""
YAML serializer.

Requires PyYaml (https://pyyaml.org/), but that's checked for in __init__.
"""

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
    # The "safe" serializer is used for better interoperability.

    def represent_decimal(self, data):
        return self.represent_scalar("tag:yaml.org,2002:str", str(data))

    def represent_time(self, data):
        # Base YAML doesn't support serialization of time types (as opposed to
        # dates or datetimes, which it does support). Converting them to
        # strings isn't perfect, but it's better than a "!!python/time" type
        # which would prevent deserialization under any other language.
        return self.represent_scalar("tag:yaml.org,2002:str", str(data))


DjangoSafeDumper.add_representer(decimal.Decimal, DjangoSafeDumper.represent_decimal)
DjangoSafeDumper.add_representer(datetime.time, DjangoSafeDumper.represent_time)


class Serializer(PythonSerializer):
    """Convert a queryset to YAML."""

    internal_use_only = False

    def end_serialization(self):
        self.options.setdefault("allow_unicode", True)
        yaml.dump(
            self.objects,
            self.stream,
            Dumper=DjangoSafeDumper,
            sort_keys=False,
            **self.options,
        )

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
