"""
Most code parts from:
https://docs.djangoproject.com/en/dev/howto/custom-model-fields/#converting-values-to-python-objects
"""
from django.db import models
from django.utils import six

@six.add_metaclass(models.SubfieldBase)
class CommaSeparatedModelField(models.CharField):
    description = "Implements comma-separated storage of lists"

    def __init__(self, separator=",", *args, **kwargs):
        self.separator = separator
        super(CommaSeparatedModelField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(CommaSeparatedModelField, self).deconstruct()
        # Only include kwarg if it's not the default
        if self.separator != ",":
            kwargs['separator'] = self.separator
        return name, path, args, kwargs

    def get_prep_value(self, value):
        return self.separator.join(value)

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if isinstance(value, (list, tuple)):
            return value

        if value is None:
            return value

        return value.split(self.separator)


class TestModel(models.Model):
    test_data = CommaSeparatedModelField(max_length=256)