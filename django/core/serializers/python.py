"""
A Python "serializer". Doesn't do much serializing per se -- just converts to
and from basic Python data types (lists, dicts, strings, etc.). Useful as a
basis for other serializers.
"""

from django.apps import apps
from django.core.serializers import base
from django.db import DEFAULT_DB_ALIAS, models
from django.db.models import CompositePrimaryKey
from django.utils.encoding import is_protected_type


class Serializer(base.Serializer):
    """
    Serialize a QuerySet to basic Python objects.
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
        self.objects.append(self.get_dump_object(obj))
        self._current = None

    def get_dump_object(self, obj):
        data = {"model": str(obj._meta)}
        if not self.use_natural_primary_keys or not hasattr(obj, "natural_key"):
            data["pk"] = self._value_from_field(obj, obj._meta.pk)
        data["fields"] = self._current
        return data

    def _value_from_field(self, obj, field):
        if isinstance(field, CompositePrimaryKey):
            return [self._value_from_field(obj, f) for f in field]
        value = field.value_from_object(obj)
        # Protected types (i.e., primitives like None, numbers, dates,
        # and Decimals) are passed through as is. All other values are
        # converted to string first.
        return value if is_protected_type(value) else field.value_to_string(obj)

    def handle_field(self, obj, field):
        self._current[field.name] = self._value_from_field(obj, field)

    def handle_fk_field(self, obj, field):
        if self.use_natural_foreign_keys and hasattr(
            field.remote_field.model, "natural_key"
        ):
            related = getattr(obj, field.name)
            if related:
                value = related.natural_key()
            else:
                value = None
        else:
            value = self._value_from_field(obj, field)
        self._current[field.name] = value

    def handle_m2m_field(self, obj, field):
        if field.remote_field.through._meta.auto_created:
            if self.use_natural_foreign_keys and hasattr(
                field.remote_field.model, "natural_key"
            ):

                def m2m_value(value):
                    return value.natural_key()

                def queryset_iterator(obj, field):
                    attr = getattr(obj, field.name)
                    chunk_size = (
                        2000 if getattr(attr, "prefetch_cache_name", None) else None
                    )
                    return attr.iterator(chunk_size)

            else:

                def m2m_value(value):
                    return self._value_from_field(value, value._meta.pk)

                def queryset_iterator(obj, field):
                    query_set = getattr(obj, field.name).select_related(None).only("pk")
                    chunk_size = 2000 if query_set._prefetch_related_lookups else None
                    return query_set.iterator(chunk_size=chunk_size)

            m2m_iter = getattr(obj, "_prefetched_objects_cache", {}).get(
                field.name,
                queryset_iterator(obj, field),
            )
            self._current[field.name] = [m2m_value(related) for related in m2m_iter]

    def getvalue(self):
        return self.objects


class Deserializer(base.Deserializer):
    """
    Deserialize simple Python objects back into Django ORM instances.

    It's expected that you pass the Python objects themselves (instead of a
    stream or a string) to the constructor
    """

    def __init__(
        self, object_list, *, using=DEFAULT_DB_ALIAS, ignorenonexistent=False, **options
    ):
        super().__init__(object_list, **options)
        self.handle_forward_references = options.pop("handle_forward_references", False)
        self.using = using
        self.ignorenonexistent = ignorenonexistent
        self.field_names_cache = {}  # Model: <list of field_names>
        self._iterator = None

    def __iter__(self):
        for obj in self.stream:
            yield from self._handle_object(obj)

    def __next__(self):
        if self._iterator is None:
            self._iterator = iter(self)
        return next(self._iterator)

    def _handle_object(self, obj):
        data = {}
        m2m_data = {}
        deferred_fields = {}

        # Look up the model and starting build a dict of data for it.
        try:
            Model = self._get_model_from_node(obj["model"])
        except base.DeserializationError:
            if self.ignorenonexistent:
                return
            raise
        if "pk" in obj:
            try:
                data[Model._meta.pk.attname] = Model._meta.pk.to_python(obj.get("pk"))
            except Exception as e:
                raise base.DeserializationError.WithData(
                    e, obj["model"], obj.get("pk"), None
                )

        if Model not in self.field_names_cache:
            self.field_names_cache[Model] = {f.name for f in Model._meta.get_fields()}
        field_names = self.field_names_cache[Model]

        # Handle each field
        for field_name, field_value in obj["fields"].items():
            if self.ignorenonexistent and field_name not in field_names:
                # skip fields no longer on model
                continue

            field = Model._meta.get_field(field_name)

            # Handle M2M relations
            if field.remote_field and isinstance(
                field.remote_field, models.ManyToManyRel
            ):
                try:
                    values = self._handle_m2m_field_node(field, field_value)
                    if values == base.DEFER_FIELD:
                        deferred_fields[field] = field_value
                    else:
                        m2m_data[field.name] = values
                except base.M2MDeserializationError as e:
                    raise base.DeserializationError.WithData(
                        e.original_exc, obj["model"], obj.get("pk"), e.pk
                    )

            # Handle FK fields
            elif field.remote_field and isinstance(
                field.remote_field, models.ManyToOneRel
            ):
                try:
                    value = self._handle_fk_field_node(field, field_value)
                    if value == base.DEFER_FIELD:
                        deferred_fields[field] = field_value
                    else:
                        data[field.attname] = value
                except Exception as e:
                    raise base.DeserializationError.WithData(
                        e, obj["model"], obj.get("pk"), field_value
                    )

            # Handle all other fields
            else:
                try:
                    data[field.name] = field.to_python(field_value)
                except Exception as e:
                    raise base.DeserializationError.WithData(
                        e, obj["model"], obj.get("pk"), field_value
                    )

        model_instance = base.build_instance(Model, data, self.using)
        yield base.DeserializedObject(model_instance, m2m_data, deferred_fields)

    def _handle_m2m_field_node(self, field, field_value):
        return base.deserialize_m2m_values(
            field, field_value, self.using, self.handle_forward_references
        )

    def _handle_fk_field_node(self, field, field_value):
        return base.deserialize_fk_value(
            field, field_value, self.using, self.handle_forward_references
        )

    @staticmethod
    def _get_model_from_node(model_identifier):
        """Look up a model from an "app_label.model_name" string."""
        try:
            return apps.get_model(model_identifier)
        except (LookupError, TypeError):
            raise base.DeserializationError(
                f"Invalid model identifier: {model_identifier}"
            )
