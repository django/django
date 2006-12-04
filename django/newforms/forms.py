"""
Form classes
"""

from fields import Field
from widgets import TextInput, Textarea
from util import ErrorDict, ErrorList, ValidationError

class DeclarativeFieldsMetaclass(type):
    "Metaclass that converts Field attributes to a dictionary called 'fields'."
    def __new__(cls, name, bases, attrs):
        attrs['fields'] = dict([(name, attrs.pop(name)) for name, obj in attrs.items() if isinstance(obj, Field)])
        return type.__new__(cls, name, bases, attrs)

class Form(object):
    "A collection of Fields, plus their associated data."
    __metaclass__ = DeclarativeFieldsMetaclass

    def __init__(self, data=None): # TODO: prefix stuff
        self.data = data or {}
        self.__data_python = None # Stores the data after to_python() has been called.
        self.__errors = None # Stores the errors after to_python() has been called.

    def __iter__(self):
        for name, field in self.fields.items():
            yield BoundField(self, field, name)

    def to_python(self):
        if self.__errors is None:
            self._validate()
        return self.__data_python

    def errors(self):
        "Returns an ErrorDict for self.data"
        if self.__errors is None:
            self._validate()
        return self.__errors

    def is_valid(self):
        """
        Returns True if the form has no errors. Otherwise, False. This exists
        solely for convenience, so client code can use positive logic rather
        than confusing negative logic ("if not form.errors()").
        """
        return not bool(self.errors())

    def __getitem__(self, name):
        "Returns a BoundField with the given name."
        try:
            field = self.fields[name]
        except KeyError:
            raise KeyError('Key %r not found in Form' % name)
        return BoundField(self, field, name)

    def _validate(self):
        data_python = {}
        errors = ErrorDict()
        for name, field in self.fields.items():
            try:
                value = field.to_python(self.data.get(name, None))
                data_python[name] = value
            except ValidationError, e:
                errors[name] = e.messages
        if not errors: # Only set self.data_python if there weren't errors.
            self.__data_python = data_python
        self.__errors = errors

class BoundField(object):
    "A Field plus data"
    def __init__(self, form, field, name):
        self._form = form
        self._field = field
        self._name = name

    def __str__(self):
        "Renders this field as an HTML widget."
        # Use the 'widget' attribute on the field to determine which type
        # of HTML widget to use.
        return self.as_widget(self._field.widget)

    def _errors(self):
        """
        Returns an ErrorList for this field. Returns an empty ErrorList
        if there are none.
        """
        try:
            return self._form.errors()[self._name]
        except KeyError:
            return ErrorList()
    errors = property(_errors)

    def as_widget(self, widget, attrs=None):
        return widget.render(self._name, self._form.data.get(self._name, None), attrs=attrs)

    def as_text(self, attrs=None):
        """
        Returns a string of HTML for representing this as an <input type="text">.
        """
        return self.as_widget(TextInput(), attrs)

    def as_textarea(self, attrs=None):
        "Returns a string of HTML for representing this as a <textarea>."
        return self.as_widget(Textarea(), attrs)
