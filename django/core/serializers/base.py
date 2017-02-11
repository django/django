"""
Module for abstract serializer/unserializer base classes.
"""
from django.db import models
from django.utils import six


class SerializerDoesNotExist(KeyError):
    """The requested serializer was not found."""
    pass


class SerializationError(Exception):
    """Something bad happened during serialization."""
    pass


class DeserializationError(Exception):
    """Something bad happened during deserialization."""

    @classmethod
    def WithData(cls, original_exc, model, fk, field_value):
        """
        Factory method for creating a deserialization error which has a more
        explanatory message.
        """
        return cls("%s: (%s:pk=%s) field_value was '%s'" % (original_exc, model, fk, field_value))


class ProgressBar(object):
    progress_width = 75

    def __init__(self, output, total_count):
        self.output = output
        self.total_count = total_count
        self.prev_done = 0

    def update(self, count):
        if not self.output:
            return
        perc = count * 100 // self.total_count
        done = perc * self.progress_width // 100
        if self.prev_done >= done:
            return
        self.prev_done = done
        cr = '' if self.total_count == 1 else '\r'
        self.output.write(cr + '[' + '.' * done + ' ' * (self.progress_width - done) + ']')
        if done == self.progress_width:
            self.output.write('\n')
        self.output.flush()


class Serializer(object):
    """
    Abstract serializer base class.
    """

    # Indicates if the implemented serializer is only available for
    # internal Django use.
    internal_use_only = False
    progress_class = ProgressBar
    stream_class = six.StringIO

    def serialize(self, queryset, **options):
        """
        Serialize a queryset.
        """
        self.options = options

        self.stream = options.pop("stream", self.stream_class())
        self.selected_fields = options.pop("fields", None)
        self.use_natural_foreign_keys = options.pop('use_natural_foreign_keys', False)
        self.use_natural_primary_keys = options.pop('use_natural_primary_keys', False)
        progress_bar = self.progress_class(
            options.pop('progress_output', None), options.pop('object_count', 0)
        )

        self.start_serialization()
        self.first = True
        for count, obj in enumerate(queryset, start=1):
            self.start_object(obj)
            # Use the concrete parent class' _meta instead of the object's _meta
            # This is to avoid local_fields problems for proxy models. Refs #17717.
            concrete_model = obj._meta.concrete_model
            for field in concrete_model._meta.local_fields:
                if field.serialize:
                    if field.remote_field is None:
                        if self.selected_fields is None or field.attname in self.selected_fields:
                            self.handle_field(obj, field)
                    else:
                        if self.selected_fields is None or field.attname[:-3] in self.selected_fields:
                            self.handle_fk_field(obj, field)
            for field in concrete_model._meta.many_to_many:
                if field.serialize:
                    if self.selected_fields is None or field.attname in self.selected_fields:
                        self.handle_m2m_field(obj, field)
            self.end_object(obj)
            progress_bar.update(count)
            if self.first:
                self.first = False
        self.end_serialization()
        return self.getvalue()

    def start_serialization(self):
        """
        Called when serializing of the queryset starts.
        """
        raise NotImplementedError('subclasses of Serializer must provide a start_serialization() method')

    def end_serialization(self):
        """
        Called when serializing of the queryset ends.
        """
        pass

    def start_object(self, obj):
        """
        Called when serializing of an object starts.
        """
        raise NotImplementedError('subclasses of Serializer must provide a start_object() method')

    def end_object(self, obj):
        """
        Called when serializing of an object ends.
        """
        pass

    def handle_field(self, obj, field):
        """
        Called to handle each individual (non-relational) field on an object.
        """
        raise NotImplementedError('subclasses of Serializer must provide an handle_field() method')

    def handle_fk_field(self, obj, field):
        """
        Called to handle a ForeignKey field.
        """
        raise NotImplementedError('subclasses of Serializer must provide an handle_fk_field() method')

    def handle_m2m_field(self, obj, field):
        """
        Called to handle a ManyToManyField.
        """
        raise NotImplementedError('subclasses of Serializer must provide an handle_m2m_field() method')

    def getvalue(self):
        """
        Return the fully serialized queryset (or None if the output stream is
        not seekable).
        """
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()


class Deserializer(six.Iterator):
    """
    Abstract base deserializer class.
    """

    def __init__(self, stream_or_string, **options):
        """
        Init this serializer given a stream or a string
        """
        self.options = options
        if isinstance(stream_or_string, six.string_types):
            self.stream = six.StringIO(stream_or_string)
        else:
            self.stream = stream_or_string

    def __iter__(self):
        return self

    def __next__(self):
        """Iteration iterface -- return the next item in the stream"""
        raise NotImplementedError('subclasses of Deserializer must provide a __next__() method')


class DeserializedObject(object):
    """
    A deserialized model.

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
        return "<%s: %s(pk=%s)>" % (
            self.__class__.__name__,
            self.object._meta.label,
            self.object.pk,
        )

    def save(self, save_m2m=True, using=None, **kwargs):
        # Call save on the Model baseclass directly. This bypasses any
        # model-defined save. The save is also forced to be raw.
        # raw=True is passed to any pre/post_save signals.
        models.Model.save_base(self.object, using=using, raw=True, **kwargs)
        if self.m2m_data and save_m2m:
            for accessor_name, object_list in self.m2m_data.items():
                getattr(self.object, accessor_name).set(object_list)

        # prevent a second (possibly accidental) call to save() from saving
        # the m2m data twice.
        self.m2m_data = None


def build_instance(Model, data, db):
    """
    Build a model instance.

    If the model instance doesn't have a primary key and the model supports
    natural keys, try to retrieve it from the database.
    """
    obj = Model(**data)
    if (obj.pk is None and hasattr(Model, 'natural_key') and
            hasattr(Model._default_manager, 'get_by_natural_key')):
        natural_key = obj.natural_key()
        try:
            obj.pk = Model._default_manager.db_manager(db).get_by_natural_key(*natural_key).pk
        except Model.DoesNotExist:
            pass
    return obj
