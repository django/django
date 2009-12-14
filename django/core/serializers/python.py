"""
A Python "serializer". Doesn't do much serializing per se -- just converts to
and from basic Python data types (lists, dicts, strings, etc.). Useful as a basis for
other serializers.
"""

from django.conf import settings
from django.core.serializers import base
from django.db import models
from django.utils.encoding import smart_unicode, is_protected_type

class Serializer(base.Serializer):
    """
    Serializes a QuerySet to basic Python objects.
    """

    internal_use_only = True

    def start_serialization(self):
        self._current = None
        self.objects = []

    def end_serialization(self):
        pass

    def start_object(self, obj):
        self._current = {}

    def end_object(self, obj):
        self.objects.append({
            "model"  : smart_unicode(obj._meta),
            "pk"     : smart_unicode(obj._get_pk_val(), strings_only=True),
            "fields" : self._current
        })
        self._current = None

    def handle_field(self, obj, field):
        value = field._get_val_from_obj(obj)
        # Protected types (i.e., primitives like None, numbers, dates,
        # and Decimals) are passed through as is. All other values are
        # converted to string first.
        if is_protected_type(value):
            self._current[field.name] = value
        else:
            self._current[field.name] = field.value_to_string(obj)

    def handle_fk_field(self, obj, field):
        related = getattr(obj, field.name)
        if related is not None:
            if self.use_natural_keys and hasattr(related, 'natural_key'):
                related = related.natural_key()
            else:
                if field.rel.field_name == related._meta.pk.name:
                    # Related to remote object via primary key
                    related = related._get_pk_val()
                else:
                    # Related to remote object via other field
                    related = smart_unicode(getattr(related, field.rel.field_name), strings_only=True)
        self._current[field.name] = related

    def handle_m2m_field(self, obj, field):
        if field.rel.through._meta.auto_created:
            if self.use_natural_keys and hasattr(field.rel.to, 'natural_key'):
                m2m_value = lambda value: value.natural_key()
            else:
                m2m_value = lambda value: smart_unicode(value._get_pk_val(), strings_only=True)
            self._current[field.name] = [m2m_value(related)
                               for related in getattr(obj, field.name).iterator()]

    def getvalue(self):
        return self.objects

def Deserializer(object_list, **options):
    """
    Deserialize simple Python objects back into Django ORM instances.

    It's expected that you pass the Python objects themselves (instead of a
    stream or a string) to the constructor
    """
    models.get_apps()
    for d in object_list:
        # Look up the model and starting build a dict of data for it.
        Model = _get_model(d["model"])
        data = {Model._meta.pk.attname : Model._meta.pk.to_python(d["pk"])}
        m2m_data = {}

        # Handle each field
        for (field_name, field_value) in d["fields"].iteritems():
            if isinstance(field_value, str):
                field_value = smart_unicode(field_value, options.get("encoding", settings.DEFAULT_CHARSET), strings_only=True)

            field = Model._meta.get_field(field_name)

            # Handle M2M relations
            if field.rel and isinstance(field.rel, models.ManyToManyRel):
                if hasattr(field.rel.to._default_manager, 'get_by_natural_key'):
                    def m2m_convert(value):
                        if hasattr(value, '__iter__'):
                            return field.rel.to._default_manager.get_by_natural_key(*value).pk
                        else:
                            return smart_unicode(field.rel.to._meta.pk.to_python(value))
                else:
                    m2m_convert = lambda v: smart_unicode(field.rel.to._meta.pk.to_python(v))
                m2m_data[field.name] = [m2m_convert(pk) for pk in field_value]

            # Handle FK fields
            elif field.rel and isinstance(field.rel, models.ManyToOneRel):
                if field_value is not None:
                    if hasattr(field.rel.to._default_manager, 'get_by_natural_key'):
                        if hasattr(field_value, '__iter__'):
                            obj = field.rel.to._default_manager.get_by_natural_key(*field_value)
                            value = getattr(obj, field.rel.field_name)
                        else:
                            value = field.rel.to._meta.get_field(field.rel.field_name).to_python(field_value)
                        data[field.attname] = value
                    else:
                        data[field.attname] = field.rel.to._meta.get_field(field.rel.field_name).to_python(field_value)
                else:
                    data[field.attname] = None

            # Handle all other fields
            else:
                data[field.name] = field.to_python(field_value)

        yield base.DeserializedObject(Model(**data), m2m_data)

def _get_model(model_identifier):
    """
    Helper to look up a model from an "app_label.module_name" string.
    """
    try:
        Model = models.get_model(*model_identifier.split("."))
    except TypeError:
        Model = None
    if Model is None:
        raise base.DeserializationError(u"Invalid model identifier: '%s'" % model_identifier)
    return Model
