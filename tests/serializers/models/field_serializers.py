import json

from django.core.serializers import register_field_serializer
from django.core.serializers.python import FieldSerializer as PythonFieldSerializer
from django.core.serializers.xml_serializer import FieldSerializer as XMLFieldSerializer
from django.core.serializers.xml_serializer import getChildrenByTagName
from django.db import models


# Example one: simple serializers that add some text around values.
class MyCharField(models.CharField):
    pass


@register_field_serializer("python", MyCharField)
class MyFieldPythonSerializer(PythonFieldSerializer):
    @classmethod
    def serialize(cls, field, obj, serializer):
        value = super().serialize(field, obj, serializer)
        return f"XXX-{value}-XXX"

    @classmethod
    def deserialize(cls, field, value, deserializer):
        value = super().deserialize(field, value, deserializer)
        return value[4:-4]


@register_field_serializer("xml", MyCharField)
class MyFieldXMLSerializer(XMLFieldSerializer):
    @classmethod
    def serialize(cls, field, obj, serializer):
        value = super().serialize(field, obj, serializer)
        return f"YYY-{value}-YYY"

    @classmethod
    def deserialize(cls, field, value, deserializer):
        value = super().deserialize(field, value, deserializer)
        return value[4:-4]


class MyFieldThing(models.Model):
    name = MyCharField(max_length=30)


# Example two: more complex serializers that handled nested model data.
class EmbeddedModelField(models.JSONField):
    def __init__(self, embedded_model, *args, **kwargs):
        self.embedded_model = embedded_model
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["embedded_model"] = self.embedded_model
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        value = super().from_db_value(value, expression, connection)
        return self.to_python(value)

    def to_python(self, value):
        """
        Pass embedded model fields' values through each field's to_python() and
        reinstantiate the embedded instance.
        """
        return self.embedded_model(
            **{
                field.attname: field.to_python(value[field.column])
                for field in self.embedded_model._meta.fields
            }
        )

    def get_db_prep_save(self, embedded_instance, connection):
        """
        Apply pre_save() and get_db_prep_save() of embedded instance fields and
        create the {field: value} dict to be saved.
        """
        field_values = {}
        add = embedded_instance._state.adding
        for field in embedded_instance._meta.fields:
            value = field.get_db_prep_save(
                field.pre_save(embedded_instance, add), connection=connection
            )
            field_values[field.column] = value
        return json.dumps(field_values)


@register_field_serializer("python", EmbeddedModelField)
class PythonSerializer:
    @classmethod
    def serialize(cls, field, obj, serializer):
        value = field.value_from_object(obj)
        return {
            subfield.name: serializer.serialize_field(subfield, value)
            for subfield in value._meta.local_fields
        }

    @classmethod
    def deserialize(cls, field, value, deserializer):
        field_values = {}
        for subfield_name, subvalue in value.items():
            subfield = field.embedded_model._meta.get_field(subfield_name)
            field_values[subfield.name] = deserializer.deserialize_field(
                subfield, subvalue, deserializer
            )
        return field.embedded_model(**field_values)


@register_field_serializer("xml", EmbeddedModelField)
class XMLSerializer:
    @classmethod
    def serialize(cls, field, obj, serializer):
        value = field.value_from_object(obj)
        serializer.start_object(obj)
        for subfield in value._meta.local_fields:
            serializer.handle_field(value, subfield)
        serializer.end_object(obj)
        return ""

    @classmethod
    def deserialize(cls, field, field_node, deserializer):
        obj = getChildrenByTagName(field_node, "object")[0]
        field_values = {}
        for subfield_node in getChildrenByTagName(obj, "field"):
            field_name = subfield_node.getAttribute("name")
            subfield = field.embedded_model._meta.get_field(field_name)
            if getChildrenByTagName(subfield_node, "None"):
                value = None
            else:
                value = deserializer.deserialize_field(
                    subfield, subfield_node, deserializer
                )
            field_values[field_name] = value
        return field.embedded_model(**field_values)


class EmbeddedAuthor(models.Model):
    name = models.CharField(max_length=255)


class Book(models.Model):
    name = models.CharField(max_length=255)
    author = EmbeddedModelField(EmbeddedAuthor)

    class Meta:
        required_db_features = {"supports_json_field"}
