"""
Form classes
"""

from django.utils.datastructures import SortedDict
from django.utils.html import escape
from fields import Field
from widgets import TextInput, Textarea, HiddenInput
from util import ErrorDict, ErrorList, ValidationError

NON_FIELD_ERRORS = '__all__'

def pretty_name(name):
    "Converts 'first_name' to 'First name'"
    name = name[0].upper() + name[1:]
    return name.replace('_', ' ')

class SortedDictFromList(SortedDict):
    "A dictionary that keeps its keys in the order in which they're inserted."
    # This is different than django.utils.datastructures.SortedDict, because
    # this takes a list/tuple as the argument to __init__().
    def __init__(self, data=None):
        if data is None: data = []
        self.keyOrder = [d[0] for d in data]
        dict.__init__(self, dict(data))

class DeclarativeFieldsMetaclass(type):
    "Metaclass that converts Field attributes to a dictionary called 'fields'."
    def __new__(cls, name, bases, attrs):
        fields = [(name, attrs.pop(name)) for name, obj in attrs.items() if isinstance(obj, Field)]
        fields.sort(lambda x, y: cmp(x[1].creation_counter, y[1].creation_counter))
        attrs['fields'] = SortedDictFromList(fields)
        return type.__new__(cls, name, bases, attrs)

class Form(object):
    "A collection of Fields, plus their associated data."
    __metaclass__ = DeclarativeFieldsMetaclass

    def __init__(self, data=None, auto_id=False): # TODO: prefix stuff
        self.ignore_errors = data is None
        self.data = data or {}
        self.auto_id = auto_id
        self.clean_data = None # Stores the data after clean() has been called.
        self.__errors = None # Stores the errors after clean() has been called.

    def __str__(self):
        return self.as_table()

    def __iter__(self):
        for name, field in self.fields.items():
            yield BoundField(self, field, name)

    def __getitem__(self, name):
        "Returns a BoundField with the given name."
        try:
            field = self.fields[name]
        except KeyError:
            raise KeyError('Key %r not found in Form' % name)
        return BoundField(self, field, name)

    def _errors(self):
        "Returns an ErrorDict for self.data"
        if self.__errors is None:
            self.full_clean()
        return self.__errors
    errors = property(_errors)

    def is_valid(self):
        """
        Returns True if the form has no errors. Otherwise, False. If errors are
        being ignored, returns False.
        """
        return not self.ignore_errors and not bool(self.errors)

    def as_table(self):
        "Returns this form rendered as HTML <tr>s -- excluding the <table></table>."
        output = []
        if self.errors.get(NON_FIELD_ERRORS):
            # Errors not corresponding to a particular field are displayed at the top.
            output.append(u'<tr><td colspan="2">%s</td></tr>' % self.non_field_errors())
        for name, field in self.fields.items():
            bf = BoundField(self, field, name)
            if bf.errors:
                output.append(u'<tr><td colspan="2">%s</td></tr>' % bf.errors)
            output.append(u'<tr><td>%s</td><td>%s</td></tr>' % (bf.label_tag(escape(bf.verbose_name+':')), bf))
        return u'\n'.join(output)

    def as_ul(self):
        "Returns this form rendered as HTML <li>s -- excluding the <ul></ul>."
        output = []
        if self.errors.get(NON_FIELD_ERRORS):
            # Errors not corresponding to a particular field are displayed at the top.
            output.append(u'<li>%s</li>' % self.non_field_errors())
        for name, field in self.fields.items():
            bf = BoundField(self, field, name)
            line = u'<li>'
            if bf.errors:
                line += str(bf.errors)
            line += u'%s %s</li>' % (bf.label_tag(escape(bf.verbose_name+':')), bf)
            output.append(line)
        return u'\n'.join(output)

    def non_field_errors(self):
        """
        Returns an ErrorList of errors that aren't associated with a particular
        field -- i.e., from Form.clean(). Returns an empty ErrorList if there
        are none.
        """
        return self.errors.get(NON_FIELD_ERRORS, ErrorList())

    def full_clean(self):
        """
        Cleans all of self.data and populates self.__errors and self.clean_data.
        """
        self.clean_data = {}
        errors = ErrorDict()
        if self.ignore_errors: # Stop further processing.
            self.__errors = errors
            return
        for name, field in self.fields.items():
            # value_from_datadict() gets the data from the dictionary.
            # Each widget type knows how to retrieve its own data, because some
            # widgets split data over several HTML fields.
            value = field.widget.value_from_datadict(self.data, name)
            try:
                value = field.clean(value)
                self.clean_data[name] = value
                if hasattr(self, 'clean_%s' % name):
                    value = getattr(self, 'clean_%s' % name)()
                self.clean_data[name] = value
            except ValidationError, e:
                errors[name] = e.messages
        try:
            self.clean_data = self.clean()
        except ValidationError, e:
            errors[NON_FIELD_ERRORS] = e.messages
        if errors:
            self.clean_data = None
        self.__errors = errors

    def clean(self):
        """
        Hook for doing any extra form-wide cleaning after Field.clean() been
        called on every field. Any ValidationError raised by this method will
        not be associated with a particular field; it will have a special-case
        association with the field named '__all__'.
        """
        return self.clean_data

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
        value = self.as_widget(self._field.widget)
        if not isinstance(value, basestring):
            # Some Widget render() methods -- notably RadioSelect -- return a
            # "special" object rather than a string. Call the __str__() on that
            # object to get its rendered value.
            value = value.__str__()
        return value

    def _errors(self):
        """
        Returns an ErrorList for this field. Returns an empty ErrorList
        if there are none.
        """
        try:
            return self._form.errors[self._name]
        except KeyError:
            return ErrorList()
    errors = property(_errors)

    def as_widget(self, widget, attrs=None):
        attrs = attrs or {}
        auto_id = self.auto_id
        if auto_id and not attrs.has_key('id') and not widget.attrs.has_key('id'):
            attrs['id'] = auto_id
        return widget.render(self._name, self.data, attrs=attrs)

    def as_text(self, attrs=None):
        """
        Returns a string of HTML for representing this as an <input type="text">.
        """
        return self.as_widget(TextInput(), attrs)

    def as_textarea(self, attrs=None):
        "Returns a string of HTML for representing this as a <textarea>."
        return self.as_widget(Textarea(), attrs)

    def as_hidden(self, attrs=None):
        """
        Returns a string of HTML for representing this as an <input type="hidden">.
        """
        return self.as_widget(HiddenInput(), attrs)

    def _data(self):
        "Returns the data for this BoundField, or None if it wasn't given."
        return self._form.data.get(self._name, None)
    data = property(_data)

    def _verbose_name(self):
        return pretty_name(self._name)
    verbose_name = property(_verbose_name)

    def label_tag(self, contents=None):
        """
        Wraps the given contents in a <label>, if the field has an ID attribute.
        Does not HTML-escape the contents. If contents aren't given, uses the
        field's HTML-escaped verbose_name.
        """
        contents = contents or escape(self.verbose_name)
        widget = self._field.widget
        id_ = widget.attrs.get('id') or self.auto_id
        if id_:
            contents = '<label for="%s">%s</label>' % (widget.id_for_label(id_), contents)
        return contents

    def _auto_id(self):
        """
        Calculates and returns the ID attribute for this BoundField, if the
        associated Form has specified auto_id. Returns an empty string otherwise.
        """
        auto_id = self._form.auto_id
        if auto_id and '%s' in str(auto_id):
            return str(auto_id) % self._name
        elif auto_id:
            return self._name
        return ''
    auto_id = property(_auto_id)
