"""
Module for abstract serializer/unserializer base classes.
"""

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from django.db import models

class SerializationError(Exception):
    """Something bad happened during serialization."""
    pass
    
class DeserializationError(Exception):
    """Something bad happened during deserialization."""
    pass

class Serializer(object):
    """
    Abstract serializer base class.
    """
    
    def serialize(self, queryset, **options):
        """
        Serialize a queryset.
        """
        self.options = options
        
        self.stream = options.get("stream", StringIO())
        
        self.start_serialization()
        for obj in queryset:
            self.start_object(obj)
            for field in obj._meta.fields:
                if field.rel is None:
                    self.handle_field(obj, field)
                else:
                    self.handle_fk_field(obj, field)
            for field in obj._meta.many_to_many:
                self.handle_m2m_field(obj, field)
            self.end_object(obj)
        self.end_serialization()
        return self.getvalue()
    
    def get_string_value(self, obj, field):
        """
        Convert a field's value to a string.
        """
        if isinstance(field, models.DateTimeField):
            value = getattr(obj, field.name).strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(field, models.FileField):
            value = getattr(obj, "get_%s_url" % field.name, lambda: None)()
        else:
            value = field.flatten_data(follow=None, obj=obj).get(field.name, "")
        return str(value)
    
    def start_serialization(self):
        """
        Called when serializing of the queryset starts.
        """
        raise NotImplementedError
    
    def end_serialization(self):
        """
        Called when serializing of the queryset ends.
        """
        pass
    
    def start_object(self, obj):
        """
        Called when serializing of an object starts.
        """
        raise NotImplementedError
    
    def end_object(self, obj):
        """
        Called when serializing of an object ends.
        """
        pass
    
    def handle_field(self, obj, field):
        """
        Called to handle each individual (non-relational) field on an object.
        """
        raise NotImplementedError
    
    def handle_fk_field(self, obj, field):
        """
        Called to handle a ForeignKey field.
        """
        raise NotImplementedError
    
    def handle_m2m_field(self, obj, field):
        """
        Called to handle a ManyToManyField.
        """
        raise NotImplementedError
    
    def getvalue(self):
        """
        Return the fully serialized queryset.
        """
        return self.stream.getvalue()

class Deserializer(object):
    """
    Abstract base deserializer class.
    """
    
    def __init__(self, stream_or_string, **options):
        """
        Init this serializer given a stream or a string
        """
        self.options = options
        if isinstance(stream_or_string, basestring):
            self.stream = StringIO(stream_or_string)
        else:
            self.stream = stream_or_string
        # hack to make sure that the models have all been loaded before
        # deserialization starts (otherwise subclass calls to get_model()
        # and friends might fail...)
        models.get_apps()
    
    def __iter__(self):
        return self
    
    def next(self):
        """Iteration iterface -- return the next item in the stream"""
        raise NotImplementedError
        
class DeserializedObject(object):
    """
    A deserialzed model.
    
    Basically a container for holding the pre-saved deserialized data along
    with the many-to-many data saved with the object.
    
    Call ``save()`` to save the object (with the many-to-many data) to the
    database; call ``save(save_m2m=False)`` to save just the object fields
    (and not touch the many-to-many stuff.)
    """
    
    def __init__(self, obj, m2m_data=None):
        self.object = obj
        self.m2m_data = m2m_data
        
    def __repr__(self):
        return "<DeserializedObject: %s>" % str(self.object)
        
    def save(self, save_m2m=True):
        self.object.save()
        if self.m2m_data and save_m2m:
            for accessor_name, object_list in self.m2m_data.items():
                setattr(self.object, accessor_name, object_list)
        
        # prevent a second (possibly accidental) call to save() from saving 
        # the m2m data twice.
        self.m2m_data = None
