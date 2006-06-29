"""
A Python "serializer". Doesn't do much serializing per se -- just converts to
and from basic Python data types (lists, dicts, strings, etc.). Useful as a basis for
other serializers.
"""

from django.conf import settings
from django.core.serializers import base
from django.db import models

class Serializer(base.Serializer):
    """
    Serializes a QuerySet to basic Python objects.
    """
    
    def start_serialization(self):
        self._current = None
        self.objects = []
        
    def end_serialization(self):
        pass
        
    def start_object(self, obj):
        self._current = {}
        
    def end_object(self, obj):
        self.objects.append({
            "model"  : str(obj._meta),
            "pk"     : str(obj._get_pk_val()),
            "fields" : self._current
        })
        self._current = None
        
    def handle_field(self, obj, field):
        self._current[field.name] = getattr(obj, field.name)
        
    def handle_fk_field(self, obj, field):
        related = getattr(obj, field.name)
        if related is not None:
            related = related._get_pk_val()
        self._current[field.name] = related
    
    def handle_m2m_field(self, obj, field):
        self._current[field.name] = [related._get_pk_val() for related in getattr(obj, field.name).iterator()]
    
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
        data = {Model._meta.pk.name : d["pk"]}
        m2m_data = {}
        
        # Handle each field
        for (field_name, field_value) in d["fields"].iteritems():
            if isinstance(field_value, unicode):
                field_value = field_value.encode(options.get("encoding", settings.DEFAULT_CHARSET))
                
            field = Model._meta.get_field(field_name)
            
            # Handle M2M relations (with in_bulk() for performance)
            if field.rel and isinstance(field.rel, models.ManyToManyRel):
                pks = []
                for pk in field_value:
                    if isinstance(pk, unicode):
                        pk = pk.encode(options.get("encoding", settings.DEFAULT_CHARSET))
                m2m_data[field.name] = field.rel.to._default_manager.in_bulk(field_value).values()
                
            # Handle FK fields
            elif field.rel and isinstance(field.rel, models.ManyToOneRel):
                try:
                    data[field.name] = field.rel.to._default_manager.get(pk=field_value)
                except RelatedModel.DoesNotExist:
                    data[field.name] = None
                    
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
        raise base.DeserializationError("Invalid model identifier: '%s'" % model_identifier)
    return Model
