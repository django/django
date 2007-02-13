"""
Form classes
"""

from django.utils.datastructures import SortedDict, MultiValueDict
from django.utils.html import escape
from fields import Field
from widgets import TextInput, Textarea, HiddenInput, MultipleHiddenInput
from util import flatatt, StrAndUnicode, ErrorDict, ErrorList, ValidationError
import copy

__all__ = ('BaseForm', 'Form')

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

    def copy(self):
        return SortedDictFromList([(k, copy.copy(v)) for k, v in self.items()])

class DeclarativeFieldsMetaclass(type):
    "Metaclass that converts Field attributes to a dictionary called 'base_fields'."
    def __new__(cls, name, bases, attrs):
        fields = [(field_name, attrs.pop(field_name)) for field_name, obj in attrs.items() if isinstance(obj, Field)]
        fields.sort(lambda x, y: cmp(x[1].creation_counter, y[1].creation_counter))
        attrs['base_fields'] = SortedDictFromList(fields)
        return type.__new__(cls, name, bases, attrs)

class BaseForm(StrAndUnicode):
    # This is the main implementation of all the Form logic. Note that this
    # class is different than Form. See the comments by the Form class for more
    # information. Any improvements to the form API should be made to *this*
    # class, not to the Form class.
    def __init__(self, data=None, auto_id='id_%s', prefix=None, initial=None):
        self.is_bound = data is not None
        self.data = data or {}
        self.auto_id = auto_id
        self.prefix = prefix
        self.initial = initial or {}
        self.__errors = None # Stores the errors after clean() has been called.
        # The base_fields class attribute is the *class-wide* definition of
        # fields. Because a particular *instance* of the class might want to
        # alter self.fields, we create self.fields here by copying base_fields.
        # Instances should always modify self.fields; they should not modify
        # self.base_fields.
        self.fields = self.base_fields.copy()

    def __unicode__(self):
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
        return self.is_bound and not bool(self.errors)

    def add_prefix(self, field_name):
        """
        Returns the field name with a prefix appended, if this Form has a
        prefix set.

        Subclasses may wish to override.
        """
        return self.prefix and ('%s-%s' % (self.prefix, field_name)) or field_name

    def _html_output(self, normal_row, error_row, row_ender, help_text_html, errors_on_separate_row):
        "Helper function for outputting HTML. Used by as_table(), as_ul(), as_p()."
        top_errors = self.non_field_errors() # Errors that should be displayed above all fields.
        output, hidden_fields = [], []
        for name, field in self.fields.items():
            bf = BoundField(self, field, name)
            bf_errors = bf.errors # Cache in local variable.
            if bf.is_hidden:
                if bf_errors:
                    top_errors.extend(['(Hidden field %s) %s' % (name, e) for e in bf_errors])
                hidden_fields.append(unicode(bf))
            else:
                if errors_on_separate_row and bf_errors:
                    output.append(error_row % bf_errors)
                label = bf.label and bf.label_tag(escape(bf.label + ':')) or ''
                if field.help_text:
                    help_text = help_text_html % field.help_text
                else:
                    help_text = u''
                output.append(normal_row % {'errors': bf_errors, 'label': label, 'field': unicode(bf), 'help_text': help_text})
        if top_errors:
            output.insert(0, error_row % top_errors)
        if hidden_fields: # Insert any hidden fields in the last row.
            str_hidden = u''.join(hidden_fields)
            if output:
                last_row = output[-1]
                # Chop off the trailing row_ender (e.g. '</td></tr>') and insert the hidden fields.
                output[-1] = last_row[:-len(row_ender)] + str_hidden + row_ender
            else: # If there aren't any rows in the output, just append the hidden fields.
                output.append(str_hidden)
        return u'\n'.join(output)

    def as_table(self):
        "Returns this form rendered as HTML <tr>s -- excluding the <table></table>."
        return self._html_output(u'<tr><th>%(label)s</th><td>%(errors)s%(field)s%(help_text)s</td></tr>', u'<tr><td colspan="2">%s</td></tr>', '</td></tr>', u'<br />%s', False)

    def as_ul(self):
        "Returns this form rendered as HTML <li>s -- excluding the <ul></ul>."
        return self._html_output(u'<li>%(errors)s%(label)s %(field)s%(help_text)s</li>', u'<li>%s</li>', '</li>', u' %s', False)

    def as_p(self):
        "Returns this form rendered as HTML <p>s."
        return self._html_output(u'<p>%(label)s %(field)s%(help_text)s</p>', u'<p>%s</p>', '</p>', u' %s', True)

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
        errors = ErrorDict()
        if not self.is_bound: # Stop further processing.
            self.__errors = errors
            return
        self.clean_data = {}
        for name, field in self.fields.items():
            # value_from_datadict() gets the data from the dictionary.
            # Each widget type knows how to retrieve its own data, because some
            # widgets split data over several HTML fields.
            value = field.widget.value_from_datadict(self.data, self.add_prefix(name))
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
            delattr(self, 'clean_data')
        self.__errors = errors

    def clean(self):
        """
        Hook for doing any extra form-wide cleaning after Field.clean() been
        called on every field. Any ValidationError raised by this method will
        not be associated with a particular field; it will have a special-case
        association with the field named '__all__'.
        """
        return self.clean_data

class Form(BaseForm):
    "A collection of Fields, plus their associated data."
    # This is a separate class from BaseForm in order to abstract the way
    # self.fields is specified. This class (Form) is the one that does the
    # fancy metaclass stuff purely for the semantic sugar -- it allows one
    # to define a form using declarative syntax.
    # BaseForm itself has no way of designating self.fields.
    __metaclass__ = DeclarativeFieldsMetaclass

class BoundField(StrAndUnicode):
    "A Field plus data"
    def __init__(self, form, field, name):
        self.form = form
        self.field = field
        self.name = name
        self.html_name = form.add_prefix(name)
        if self.field.label is None:
            self.label = pretty_name(name)
        else:
            self.label = self.field.label

    def __unicode__(self):
        "Renders this field as an HTML widget."
        # Use the 'widget' attribute on the field to determine which type
        # of HTML widget to use.
        value = self.as_widget(self.field.widget)
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
        return self.form.errors.get(self.name, ErrorList())
    errors = property(_errors)

    def as_widget(self, widget, attrs=None):
        attrs = attrs or {}
        auto_id = self.auto_id
        if auto_id and not attrs.has_key('id') and not widget.attrs.has_key('id'):
            attrs['id'] = auto_id
        if not self.form.is_bound:
            data = self.form.initial.get(self.name, self.field.initial)
        else:
            data = self.data
        return widget.render(self.html_name, data, attrs=attrs)

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
        return self.as_widget(self.field.hidden_widget(), attrs)

    def _data(self):
        """
        Returns the data for this BoundField, or None if it wasn't given.
        """
        return self.field.widget.value_from_datadict(self.form.data, self.html_name)
    data = property(_data)

    def label_tag(self, contents=None, attrs=None):
        """
        Wraps the given contents in a <label>, if the field has an ID attribute.
        Does not HTML-escape the contents. If contents aren't given, uses the
        field's HTML-escaped label.

        If attrs are given, they're used as HTML attributes on the <label> tag.
        """
        contents = contents or escape(self.label)
        widget = self.field.widget
        id_ = widget.attrs.get('id') or self.auto_id
        if id_:
            attrs = attrs and flatatt(attrs) or ''
            contents = '<label for="%s"%s>%s</label>' % (widget.id_for_label(id_), attrs, contents)
        return contents

    def _is_hidden(self):
        "Returns True if this BoundField's widget is hidden."
        return self.field.widget.is_hidden
    is_hidden = property(_is_hidden)

    def _auto_id(self):
        """
        Calculates and returns the ID attribute for this BoundField, if the
        associated Form has specified auto_id. Returns an empty string otherwise.
        """
        auto_id = self.form.auto_id
        if auto_id and '%s' in str(auto_id):
            return str(auto_id) % self.html_name
        elif auto_id:
            return self.html_name
        return ''
    auto_id = property(_auto_id)
