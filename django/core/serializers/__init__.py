"""
Interfaces for serializing Django objects.

Usage::

    from django.core import serializers
    json = serializers.serialize("json", some_query_set)
    objects = list(serializers.deserialize("json", json))

To add your own serializers, use the SERIALIZATION_MODULES setting::

    SERIALIZATION_MODULES = {
        "csv" : "path.to.csv.serializer",
        "txt" : "path.to.txt.serializer",
    }

"""

from django.conf import settings

# Built-in serializers
BUILTIN_SERIALIZERS = {
    "xml"    : "django.core.serializers.xml_serializer",
    "python" : "django.core.serializers.python",
    "json"   : "django.core.serializers.json",
}

# Check for PyYaml and register the serializer if it's available.
try:
    import yaml
    BUILTIN_SERIALIZERS["yaml"] = "django.core.serializers.pyyaml"
except ImportError:
    pass

_serializers = {}

def register_serializer(format, serializer_module):
    """Register a new serializer by passing in a module name."""
    module = __import__(serializer_module, {}, {}, [''])
    _serializers[format] = module

def unregister_serializer(format):
    """Unregister a given serializer"""
    del _serializers[format]

def get_serializer(format):
    if not _serializers:
        _load_serializers()
    return _serializers[format].Serializer

def get_serializer_formats():
    if not _serializers:
        _load_serializers()
    return _serializers.keys()

def get_public_serializer_formats():
    if not _serializers:
        _load_serializers()
    return [k for k, v in _serializers.iteritems() if not v.Serializer.internal_use_only]

def get_deserializer(format):
    if not _serializers:
        _load_serializers()
    return _serializers[format].Deserializer

def serialize(format, queryset, **options):
    """
    Serialize a queryset (or any iterator that returns database objects) using
    a certain serializer.
    """
    s = get_serializer(format)()
    s.serialize(queryset, **options)
    return s.getvalue()

def deserialize(format, stream_or_string):
    """
    Deserialize a stream or a string. Returns an iterator that yields ``(obj,
    m2m_relation_dict)``, where ``obj`` is a instantiated -- but *unsaved* --
    object, and ``m2m_relation_dict`` is a dictionary of ``{m2m_field_name :
    list_of_related_objects}``.
    """
    d = get_deserializer(format)
    return d(stream_or_string)

def _load_serializers():
    """
    Register built-in and settings-defined serializers. This is done lazily so
    that user code has a chance to (e.g.) set up custom settings without
    needing to be careful of import order.
    """
    for format in BUILTIN_SERIALIZERS:
        register_serializer(format, BUILTIN_SERIALIZERS[format])
    if hasattr(settings, "SERIALIZATION_MODULES"):
        for format in settings.SERIALIZATION_MODULES:
            register_serializer(format, settings.SERIALIZATION_MODULES[format])
