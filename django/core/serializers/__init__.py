"""
Interfaces for serializing Django objects.

Usage::

    from django.core import serializers
    json = serializers.serialize("json", some_queryset)
    objects = list(serializers.deserialize("json", json))

To add your own serializers, use the SERIALIZATION_MODULES setting::

    SERIALIZATION_MODULES = {
        "csv": "path.to.csv.serializer",
        "txt": "path.to.txt.serializer",
    }

"""

import importlib

from django.apps import apps
from django.conf import settings
from django.core.serializers.base import SerializerDoesNotExist
from django.utils import six

# Built-in serializers
BUILTIN_SERIALIZERS = {
    "xml": "django.core.serializers.xml_serializer",
    "python": "django.core.serializers.python",
    "json": "django.core.serializers.json",
    "yaml": "django.core.serializers.pyyaml",
}

_serializers = {}


class BadSerializer(object):
    """
    Stub serializer to hold exception raised during registration

    This allows the serializer registration to cache serializers and if there
    is an error raised in the process of creating a serializer it will be
    raised and passed along to the caller when the serializer is used.
    """
    internal_use_only = False

    def __init__(self, exception):
        self.exception = exception

    def __call__(self, *args, **kwargs):
        raise self.exception


def register_serializer(format, serializer_module, serializers=None):
    """Register a new serializer.

    ``serializer_module`` should be the fully qualified module name
    for the serializer.

    If ``serializers`` is provided, the registration will be added
    to the provided dictionary.

    If ``serializers`` is not provided, the registration will be made
    directly into the global register of serializers. Adding serializers
    directly is not a thread-safe operation.
    """
    if serializers is None and not _serializers:
        _load_serializers()

    try:
        module = importlib.import_module(serializer_module)
    except ImportError as exc:
        bad_serializer = BadSerializer(exc)

        module = type('BadSerializerModule', (object,), {
            'Deserializer': bad_serializer,
            'Serializer': bad_serializer,
        })

    if serializers is None:
        _serializers[format] = module
    else:
        serializers[format] = module


def unregister_serializer(format):
    "Unregister a given serializer. This is not a thread-safe operation."
    if not _serializers:
        _load_serializers()
    if format not in _serializers:
        raise SerializerDoesNotExist(format)
    del _serializers[format]


def get_serializer(format):
    if not _serializers:
        _load_serializers()
    if format not in _serializers:
        raise SerializerDoesNotExist(format)
    return _serializers[format].Serializer


def get_serializer_formats():
    if not _serializers:
        _load_serializers()
    return list(_serializers)


def get_public_serializer_formats():
    if not _serializers:
        _load_serializers()
    return [k for k, v in six.iteritems(_serializers) if not v.Serializer.internal_use_only]


def get_deserializer(format):
    if not _serializers:
        _load_serializers()
    if format not in _serializers:
        raise SerializerDoesNotExist(format)
    return _serializers[format].Deserializer


def serialize(format, queryset, **options):
    """
    Serialize a queryset (or any iterator that returns database objects) using
    a certain serializer.
    """
    s = get_serializer(format)()
    s.serialize(queryset, **options)
    return s.getvalue()


def deserialize(format, stream_or_string, **options):
    """
    Deserialize a stream or a string. Returns an iterator that yields ``(obj,
    m2m_relation_dict)``, where ``obj`` is an instantiated -- but *unsaved* --
    object, and ``m2m_relation_dict`` is a dictionary of ``{m2m_field_name :
    list_of_related_objects}``.
    """
    d = get_deserializer(format)
    return d(stream_or_string, **options)


def _load_serializers():
    """
    Register built-in and settings-defined serializers. This is done lazily so
    that user code has a chance to (e.g.) set up custom settings without
    needing to be careful of import order.
    """
    global _serializers
    serializers = {}
    for format in BUILTIN_SERIALIZERS:
        register_serializer(format, BUILTIN_SERIALIZERS[format], serializers)
    if hasattr(settings, "SERIALIZATION_MODULES"):
        for format in settings.SERIALIZATION_MODULES:
            register_serializer(format, settings.SERIALIZATION_MODULES[format], serializers)
    _serializers = serializers


def sort_dependencies(app_list):
    """Sort a list of (app_config, models) pairs into a single list of models.

    The single list of models is sorted so that any model with a natural key
    is serialized before a normal model, and any model with a natural key
    dependency has it's dependencies serialized first.
    """
    # Process the list of models, and get the list of dependencies
    model_dependencies = []
    models = set()
    for app_config, model_list in app_list:
        if model_list is None:
            model_list = app_config.get_models()

        for model in model_list:
            models.add(model)
            # Add any explicitly defined dependencies
            if hasattr(model, 'natural_key'):
                deps = getattr(model.natural_key, 'dependencies', [])
                if deps:
                    deps = [apps.get_model(dep) for dep in deps]
            else:
                deps = []

            # Now add a dependency for any FK relation with a model that
            # defines a natural key
            for field in model._meta.fields:
                if field.remote_field:
                    rel_model = field.remote_field.model
                    if hasattr(rel_model, 'natural_key') and rel_model != model:
                        deps.append(rel_model)
            # Also add a dependency for any simple M2M relation with a model
            # that defines a natural key.  M2M relations with explicit through
            # models don't count as dependencies.
            for field in model._meta.many_to_many:
                if field.remote_field.through._meta.auto_created:
                    rel_model = field.remote_field.model
                    if hasattr(rel_model, 'natural_key') and rel_model != model:
                        deps.append(rel_model)
            model_dependencies.append((model, deps))

    model_dependencies.reverse()
    # Now sort the models to ensure that dependencies are met. This
    # is done by repeatedly iterating over the input list of models.
    # If all the dependencies of a given model are in the final list,
    # that model is promoted to the end of the final list. This process
    # continues until the input list is empty, or we do a full iteration
    # over the input models without promoting a model to the final list.
    # If we do a full iteration without a promotion, that means there are
    # circular dependencies in the list.
    model_list = []
    while model_dependencies:
        skipped = []
        changed = False
        while model_dependencies:
            model, deps = model_dependencies.pop()

            # If all of the models in the dependency list are either already
            # on the final model list, or not on the original serialization list,
            # then we've found another model with all it's dependencies satisfied.
            found = True
            for candidate in ((d not in models or d in model_list) for d in deps):
                if not candidate:
                    found = False
            if found:
                model_list.append(model)
                changed = True
            else:
                skipped.append((model, deps))
        if not changed:
            raise RuntimeError(
                "Can't resolve dependencies for %s in serialized app list." %
                ', '.join(
                    '%s.%s' % (model._meta.app_label, model._meta.object_name)
                    for model, deps in sorted(skipped, key=lambda obj: obj[0].__name__)
                )
            )
        model_dependencies = skipped

    return model_list
