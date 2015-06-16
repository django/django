"""
Most code parts from:
https://docs.djangoproject.com/en/dev/howto/custom-model-fields/#converting-values-to-python-objects
"""
from django.db import models

class CommaSeparatedModelField1(models.CharField):
    description = "Implements comma-separated storage of lists"

    def __init__(self, separator=",", *args, **kwargs):
        self.separator = separator
        super(CommaSeparatedModelField1, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(CommaSeparatedModelField1, self).deconstruct()
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


class TestModel1(models.Model):
    test_data = CommaSeparatedModelField1(max_length=256)


class CommaSeparatedModelField2(CommaSeparatedModelField1):
    __metaclass__ = models.SubfieldBase


class TestModel2(models.Model):
    test_data = CommaSeparatedModelField2(max_length=256)