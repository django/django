from django.core import validators
from django.core.exceptions import PermissionDenied
from django.utils.html import escape
from django.conf import settings
from django.utils.translation import gettext, ngettext

FORM_FIELD_ID_PREFIX = 'id_'

class EmptyValue(Exception):
    "This is raised when empty data is provided"
    pass

class Manipulator(object):
    # List of permission strings. User must have at least one to manipulate.
    # None means everybody has permission.
    required_permission = ''

    def __init__(self):
        # List of FormField objects
        self.fields = []

    def __getitem__(self, field_name):
        "Looks up field by field name; raises KeyError on failure"
        for field in self.fields:
            if field.field_name == field_name:
                return field
        raise KeyError, "Field %s not found\n%s" % (field_name, repr(self.fields))

    def __delitem__(self, field_name):
        "Deletes the field with the given field name; raises KeyError on failure"
        for i, field in enumerate(self.fields):
            if field.field_name == field_name:
                del self.fields[i]
                return
        raise KeyError, "Field %s not found" % field_name

    def check_permissions(self, user):
        """Confirms user has required permissions to use this manipulator; raises
        PermissionDenied on failure."""
        if self.required_permission is None:
            return
        if user.has_perm(self.required_permission):
            return
        raise PermissionDenied

    def prepare(self, new_data):
        """
        Makes any necessary preparations to new_data, in place, before data has
        been validated.
        """
        for field in self.fields:
            field.prepare(new_data)

    def get_validation_errors(self, new_data):
        "Returns dictionary mapping field_names to error-message lists"
        errors = {}
        self.prepare(new_data)
        for field in self.fields:
            errors.update(field.get_validation_errors(new_data))
            val_name = 'validate_%s' % field.field_name
            if hasattr(self, val_name):
                val = getattr(self, val_name)
                try:
                    field.run_validator(new_data, val)
                except (validators.ValidationError, validators.CriticalValidationError), e:
                    errors.setdefault(field.field_name, []).extend(e.messages)

#            if field.is_required and not new_data.get(field.field_name, False):
#                errors.setdefault(field.field_name, []).append(gettext_lazy('This field is required.'))
#                continue
#            try:
#                validator_list = field.validator_list
#                if hasattr(self, 'validate_%s' % field.field_name):
#                    validator_list.append(getattr(self, 'validate_%s' % field.field_name))
#                for validator in validator_list:
#                    if field.is_required or new_data.get(field.field_name, False) or hasattr(validator, 'always_test'):
#                        try:
#                            if hasattr(field, 'requires_data_list'):
#                                validator(new_data.getlist(field.field_name), new_data)
#                            else:
#                                validator(new_data.get(field.field_name, ''), new_data)
#                        except validators.ValidationError, e:
#                            errors.setdefault(field.field_name, []).extend(e.messages)
#            # If a CriticalValidationError is raised, ignore any other ValidationErrors
#            # for this particular field
#            except validators.CriticalValidationError, e:
#                errors.setdefault(field.field_name, []).extend(e.messages)
        return errors

    def save(self, new_data):
        "Saves the changes and returns the new object"
        # changes is a dictionary-like object keyed by field_name
        raise NotImplementedError

    def do_html2python(self, new_data):
        """
        Convert the data from HTML data types to Python datatypes, changing the
        object in place. This happens after validation but before storage. This
        must happen after validation because html2python functions aren't
        expected to deal with invalid input.
        """
        for field in self.fields:
            field.convert_post_data(new_data)

class FormWrapper(object):
    """
    A wrapper linking a Manipulator to the template system.
    This allows dictionary-style lookups of formfields. It also handles feeding
    prepopulated data and validation error messages to the formfield objects.
    """
    def __init__(self, manipulator, data, error_dict, edit_inline=True):
        self.manipulator, self.data = manipulator, data
        self.error_dict = error_dict
        self._inline_collections = None
        self.edit_inline = edit_inline

    def __repr__(self):
        return repr(self.__dict__)

    def __getitem__(self, key):
        for field in self.manipulator.fields:
            if field.field_name == key:
                data = field.extract_data(self.data)
                return FormFieldWrapper(field, data, self.error_dict.get(field.field_name, []))
        if self.edit_inline:
            self.fill_inline_collections()
            for inline_collection in self._inline_collections:
                if inline_collection.name == key:
                    return inline_collection
        raise KeyError, "Could not find Formfield or InlineObjectCollection named %r" % key

    def fill_inline_collections(self):
        if not self._inline_collections:
            ic = []
            related_objects = self.manipulator.get_related_objects()
            for rel_obj in related_objects:
                data = rel_obj.extract_data(self.data)
                inline_collection = InlineObjectCollection(self.manipulator, rel_obj, data, self.error_dict)
                ic.append(inline_collection)
            self._inline_collections = ic

    def has_errors(self):
        return self.error_dict != {}

    def _get_fields(self):
        try:
            return self._fields
        except AttributeError:
            self._fields = [self.__getitem__(field.field_name) for field in self.manipulator.fields]
            return self._fields

    fields = property(_get_fields)

class FormFieldWrapper(object):
    "A bridge between the template system and an individual form field. Used by FormWrapper."
    def __init__(self, formfield, data, error_list):
        self.formfield, self.data, self.error_list = formfield, data, error_list
        self.field_name = self.formfield.field_name # for convenience in templates

    def __str__(self):
        "Renders the field"
        return str(self.formfield.render(self.data))

    def __repr__(self):
        return '<FormFieldWrapper for "%s">' % self.formfield.field_name

    def field_list(self):
        """
        Like __str__(), but returns a list. Use this when the field's render()
        method returns a list.
        """
        return self.formfield.render(self.data)

    def errors(self):
        return self.error_list

    def html_error_list(self):
        if self.errors():
            return '<ul class="errorlist"><li>%s</li></ul>' % '</li><li>'.join([escape(e) for e in self.errors()])
        else:
            return ''

    def get_id(self):
        return self.formfield.get_id()

class FormFieldCollection(FormFieldWrapper):
    "A utility class that gives the template access to a dict of FormFieldWrappers"
    def __init__(self, formfield_dict):
        self.formfield_dict = formfield_dict

    def __str__(self):
        return str(self.formfield_dict)

    def __getitem__(self, template_key):
        "Look up field by template key; raise KeyError on failure"
        return self.formfield_dict[template_key]

    def __repr__(self):
        return "<FormFieldCollection: %s>" % self.formfield_dict

    def errors(self):
        "Returns list of all errors in this collection's formfields"
        errors = []
        for field in self.formfield_dict.values():
            if hasattr(field, 'errors'):
                errors.extend(field.errors())
        return errors

    def has_errors(self):
        return bool(len(self.errors()))

    def html_combined_error_list(self):
        return ''.join([field.html_error_list() for field in self.formfield_dict.values() if hasattr(field, 'errors')])

class InlineObjectCollection(object):
    "An object that acts like a sparse list of form field collections."
    def __init__(self, parent_manipulator, rel_obj, data, errors):
        self.parent_manipulator = parent_manipulator
        self.rel_obj = rel_obj
        self.data = data
        self.errors = errors
        self._collections = None
        self.name = rel_obj.name

    def __len__(self):
        self.fill()
        return self._collections.__len__()

    def __getitem__(self, k):
        self.fill()
        return self._collections.__getitem__(k)

    def __setitem__(self, k, v):
        self.fill()
        return self._collections.__setitem__(k,v)

    def __delitem__(self, k):
        self.fill()
        return self._collections.__delitem__(k)

    def __iter__(self):
        self.fill()
        return iter(self._collections.values())

    def items(self):
        self.fill()
        return self._collections.items()

    def fill(self):
        if self._collections:
            return
        else:
            var_name = self.rel_obj.opts.object_name.lower()
            collections = {}
            orig = None
            if hasattr(self.parent_manipulator, 'original_object'):
                orig = self.parent_manipulator.original_object
            orig_list = self.rel_obj.get_list(orig)

            for i, instance in enumerate(orig_list):
                collection = {'original': instance}
                for f in self.rel_obj.editable_fields():
                    for field_name in f.get_manipulator_field_names(''):
                        full_field_name = '%s.%d.%s' % (var_name, i, field_name)
                        field = self.parent_manipulator[full_field_name]
                        data = field.extract_data(self.data)
                        errors = self.errors.get(full_field_name, [])
                        collection[field_name] = FormFieldWrapper(field, data, errors)
                collections[i] = FormFieldCollection(collection)
            self._collections = collections


class FormField(object):
    """Abstract class representing a form field.

    Classes that extend FormField should define the following attributes:
        field_name
            The field's name for use by programs.
        validator_list
            A list of validation tests (callback functions) that the data for
            this field must pass in order to be added or changed.
        is_required
            A Boolean. Is it a required field?
    Subclasses should also implement a render(data) method, which is responsible
    for rending the form field in XHTML.
    """
    def __str__(self):
        return self.render('')

    def __repr__(self):
        return 'FormField "%s"' % self.field_name

    def prepare(self, new_data):
        "Hook for doing something to new_data (in place) before validation."
        pass

    def html2python(data):
        "Hook for converting an HTML datatype (e.g. 'on' for checkboxes) to a Python type"
        return data
    html2python = staticmethod(html2python)

    def render(self, data):
        raise NotImplementedError

    def get_member_name(self):
        if hasattr(self, 'member_name'):
            return self.member_name
        else:
            return self.field_name

    def extract_data(self, data_dict):
        if hasattr(self, 'requires_data_list') and hasattr(data_dict, 'getlist'):
            data = data_dict.getlist(self.get_member_name())
        else:
            data = data_dict.get(self.get_member_name(), None)
        if data is None:
            data = ''
        return data

    def convert_post_data(self, new_data):
        name = self.get_member_name()
        if new_data.has_key(self.field_name):
            d = new_data.getlist(self.field_name)
            try:
                converted_data = [self.__class__.html2python(data) for data in d]
            except ValueError:
                converted_data = d
            new_data.setlist(name, converted_data)
        else:
            try:
                #individual fields deal with None values themselves
                new_data.setlist(name, [self.__class__.html2python(None)])
            except EmptyValue:
                new_data.setlist(name, [])


    def run_validator(self, new_data, validator):
        if self.is_required or new_data.get(self.field_name, False) or hasattr(validator, 'always_test'):
            if hasattr(self, 'requires_data_list'):
                validator(new_data.getlist(self.field_name), new_data)
            else:
                validator(new_data.get(self.field_name, ''), new_data)

    def get_validation_errors(self, new_data):
        errors = {}
        if self.is_required and not new_data.get(self.field_name, False):
            errors.setdefault(self.field_name, []).append(gettext('This field is required.'))
            return errors
        try:
            for validator in self.validator_list:
                try:
                    self.run_validator(new_data, validator)
                except validators.ValidationError, e:
                    errors.setdefault(self.field_name, []).extend(e.messages)
        # If a CriticalValidationError is raised, ignore any other ValidationErrors
        # for this particular field
        except validators.CriticalValidationError, e:
            errors.setdefault(self.field_name, []).extend(e.messages)
        return errors

    def get_id(self):
        "Returns the HTML 'id' attribute for this form field."
        return FORM_FIELD_ID_PREFIX + self.field_name

####################
# GENERIC WIDGETS  #
####################

class TextField(FormField):
    input_type = "text"
    def __init__(self, field_name, length=30, maxlength=None, is_required=False, validator_list=None, member_name=None):
        if validator_list is None: validator_list = []
        self.field_name = field_name
        self.length, self.maxlength = length, maxlength
        self.is_required = is_required
        self.validator_list = [self.isValidLength, self.hasNoNewlines] + validator_list
        if member_name != None:
            self.member_name = member_name

    def isValidLength(self, data, form):
        if data and self.maxlength and len(data.decode(settings.DEFAULT_CHARSET)) > self.maxlength:
            raise validators.ValidationError, ngettext("Ensure your text is less than %s character.",
                "Ensure your text is less than %s characters.", self.maxlength) % self.maxlength

    def hasNoNewlines(self, data, form):
        if data and '\n' in data:
            raise validators.ValidationError, gettext("Line breaks are not allowed here.")

    def render(self, data):
        if data is None:
            data = ''
        maxlength = ''
        if self.maxlength:
            maxlength = 'maxlength="%s" ' % self.maxlength
        if isinstance(data, unicode):
            data = data.encode(settings.DEFAULT_CHARSET)
        return '<input type="%s" id="%s" class="v%s%s" name="%s" size="%s" value="%s" %s/>' % \
            (self.input_type, self.get_id(), self.__class__.__name__, self.is_required and ' required' or '',
            self.field_name, self.length, escape(data), maxlength)

    def html2python(data):
        return data
    html2python = staticmethod(html2python)

class PasswordField(TextField):
    input_type = "password"

class LargeTextField(TextField):
    def __init__(self, field_name, rows=10, cols=40, is_required=False, validator_list=None, maxlength=None):
        if validator_list is None: validator_list = []
        self.field_name = field_name
        self.rows, self.cols, self.is_required = rows, cols, is_required
        self.validator_list = validator_list[:]
        if maxlength:
            self.validator_list.append(self.isValidLength)
            self.maxlength = maxlength

    def render(self, data):
        if data is None:
            data = ''
        if isinstance(data, unicode):
            data = data.encode(settings.DEFAULT_CHARSET)
        return '<textarea id="%s" class="v%s%s" name="%s" rows="%s" cols="%s">%s</textarea>' % \
            (self.get_id(), self.__class__.__name__, self.is_required and ' required' or '',
            self.field_name, self.rows, self.cols, escape(data))

class HiddenField(FormField):
    def __init__(self, field_name, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        self.field_name, self.is_required = field_name, is_required
        self.validator_list = validator_list[:]

    def render(self, data):
        return '<input type="hidden" id="%s" name="%s" value="%s" />' % \
            (self.get_id(), self.field_name, escape(data))

class CheckboxField(FormField):
    def __init__(self, field_name, checked_by_default=False, validator_list=None, is_required=False):
        if validator_list is None: validator_list = []
        self.field_name = field_name
        self.checked_by_default = checked_by_default
        self.is_required = is_required
        self.validator_list = validator_list[:]

    def render(self, data):
        checked_html = ''
        if data or (data is '' and self.checked_by_default):
            checked_html = ' checked="checked"'
        return '<input type="checkbox" id="%s" class="v%s" name="%s"%s />' % \
            (self.get_id(), self.__class__.__name__,
            self.field_name, checked_html)

    def html2python(data):
        "Convert value from browser ('on' or '') to a Python boolean"
        if data == 'on':
            return True
        return False
    html2python = staticmethod(html2python)

class SelectField(FormField):
    def __init__(self, field_name, choices=None, size=1, is_required=False, validator_list=None, member_name=None):
        if validator_list is None: validator_list = []
        if choices is None: choices = []
        self.field_name = field_name
        # choices is a list of (value, human-readable key) tuples because order matters
        self.choices, self.size, self.is_required = choices, size, is_required
        self.validator_list = [self.isValidChoice] + validator_list
        if member_name != None:
            self.member_name = member_name

    def render(self, data):
        output = ['<select id="%s" class="v%s%s" name="%s" size="%s">' % \
            (self.get_id(), self.__class__.__name__,
             self.is_required and ' required' or '', self.field_name, self.size)]
        str_data = str(data) # normalize to string
        for value, display_name in self.choices:
            selected_html = ''
            if str(value) == str_data:
                selected_html = ' selected="selected"'
            output.append('    <option value="%s"%s>%s</option>' % (escape(value), selected_html, escape(display_name)))
        output.append('  </select>')
        return '\n'.join(output)

    def isValidChoice(self, data, form):
        str_data = str(data)
        str_choices = [str(item[0]) for item in self.choices]
        if str_data not in str_choices:
            raise validators.ValidationError, gettext("Select a valid choice; '%(data)s' is not in %(choices)s.") % {'data': str_data, 'choices': str_choices}

class NullSelectField(SelectField):
    "This SelectField converts blank fields to None"
    def html2python(data):
        if not data:
            return None
        return data
    html2python = staticmethod(html2python)

class RadioSelectField(FormField):
    def __init__(self, field_name, choices=None, ul_class='', is_required=False, validator_list=None, member_name=None):
        if validator_list is None: validator_list = []
        if choices is None: choices = []
        self.field_name = field_name
        # choices is a list of (value, human-readable key) tuples because order matters
        self.choices, self.is_required = choices, is_required
        self.validator_list = [self.isValidChoice] + validator_list
        self.ul_class = ul_class
        if member_name != None:
            self.member_name = member_name

    def render(self, data):
        """
        Returns a special object, RadioFieldRenderer, that is iterable *and*
        has a default str() rendered output.

        This allows for flexible use in templates. You can just use the default
        rendering:

            {{ field_name }}

        ...which will output the radio buttons in an unordered list.
        Or, you can manually traverse each radio option for special layout:

            {% for option in field_name.field_list %}
                {{ option.field }} {{ option.label }}<br />
            {% endfor %}
        """
        class RadioFieldRenderer:
            def __init__(self, datalist, ul_class):
                self.datalist, self.ul_class = datalist, ul_class
            def __str__(self):
                "Default str() output for this radio field -- a <ul>"
                output = ['<ul%s>' % (self.ul_class and ' class="%s"' % self.ul_class or '')]
                output.extend(['<li>%s %s</li>' % (d['field'], d['label']) for d in self.datalist])
                output.append('</ul>')
                return ''.join(output)
            def __iter__(self):
                for d in self.datalist:
                    yield d
            def __len__(self):
                return len(self.datalist)
        datalist = []
        str_data = str(data) # normalize to string
        for i, (value, display_name) in enumerate(self.choices):
            selected_html = ''
            if str(value) == str_data:
                selected_html = ' checked="checked"'
            datalist.append({
                'value': value,
                'name': display_name,
                'field': '<input type="radio" id="%s" name="%s" value="%s"%s/>' % \
                    (self.get_id() + '_' + str(i), self.field_name, value, selected_html),
                'label': '<label for="%s">%s</label>' % \
                    (self.get_id() + '_' + str(i), display_name),
            })
        return RadioFieldRenderer(datalist, self.ul_class)

    def isValidChoice(self, data, form):
        str_data = str(data)
        str_choices = [str(item[0]) for item in self.choices]
        if str_data not in str_choices:
            raise validators.ValidationError, gettext("Select a valid choice; '%(data)s' is not in %(choices)s.") % {'data':str_data, 'choices':str_choices}

class NullBooleanField(SelectField):
    "This SelectField provides 'Yes', 'No' and 'Unknown', mapping results to True, False or None"
    def __init__(self, field_name, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        SelectField.__init__(self, field_name, choices=[('1', 'Unknown'), ('2', 'Yes'), ('3', 'No')],
            is_required=is_required, validator_list=validator_list)

    def render(self, data):
        if data is None: data = '1'
        elif data == True: data = '2'
        elif data == False: data = '3'
        return SelectField.render(self, data)

    def html2python(data):
        return {None: None, '1': None, '2': True, '3': False}[data]
    html2python = staticmethod(html2python)

class SelectMultipleField(SelectField):
    requires_data_list = True
    def render(self, data):
        output = ['<select id="%s" class="v%s%s" name="%s" size="%s" multiple="multiple">' % \
            (self.get_id(), self.__class__.__name__, self.is_required and ' required' or '',
            self.field_name, self.size)]
        str_data_list = map(str, data) # normalize to strings
        for value, choice in self.choices:
            selected_html = ''
            if str(value) in str_data_list:
                selected_html = ' selected="selected"'
            output.append('    <option value="%s"%s>%s</option>' % (escape(value), selected_html, escape(choice)))
        output.append('  </select>')
        return '\n'.join(output)

    def isValidChoice(self, field_data, all_data):
        # data is something like ['1', '2', '3']
        str_choices = [str(item[0]) for item in self.choices]
        for val in map(str, field_data):
            if val not in str_choices:
                raise validators.ValidationError, gettext("Select a valid choice; '%(data)s' is not in %(choices)s.") % {'data':val, 'choices':str_choices}

    def html2python(data):
        if data is None:
            raise EmptyValue
        return data
    html2python = staticmethod(html2python)

class CheckboxSelectMultipleField(SelectMultipleField):
    """
    This has an identical interface to SelectMultipleField, except the rendered
    widget is different. Instead of a <select multiple>, this widget outputs a
    <ul> of <input type="checkbox">es.

    Of course, that results in multiple form elements for the same "single"
    field, so this class's prepare() method flattens the split data elements
    back into the single list that validators, renderers and save() expect.
    """
    requires_data_list = True
    def __init__(self, field_name, choices=None, ul_class='', validator_list=None):
        if validator_list is None: validator_list = []
        if choices is None: choices = []
        self.ul_class = ul_class
        SelectMultipleField.__init__(self, field_name, choices, size=1, is_required=False, validator_list=validator_list)

    def prepare(self, new_data):
        # new_data has "split" this field into several fields, so flatten it
        # back into a single list.
        data_list = []
        for value, readable_value in self.choices:
            if new_data.get('%s%s' % (self.field_name, value), '') == 'on':
                data_list.append(value)
        new_data.setlist(self.field_name, data_list)

    def render(self, data):
        output = ['<ul%s>' % (self.ul_class and ' class="%s"' % self.ul_class or '')]
        str_data_list = map(str, data) # normalize to strings
        for value, choice in self.choices:
            checked_html = ''
            if str(value) in str_data_list:
                checked_html = ' checked="checked"'
            field_name = '%s%s' % (self.field_name, value)
            output.append('<li><input type="checkbox" id="%s" class="v%s" name="%s"%s value="on" /> <label for="%s">%s</label></li>' % \
                (self.get_id() + escape(value), self.__class__.__name__, field_name, checked_html,
                self.get_id() + escape(value), choice))
        output.append('</ul>')
        return '\n'.join(output)

####################
# FILE UPLOADS     #
####################

class FileUploadField(FormField):
    def __init__(self, field_name, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        self.field_name, self.is_required = field_name, is_required
        self.validator_list = [self.isNonEmptyFile] + validator_list

    def isNonEmptyFile(self, field_data, all_data):
        try:
            content = field_data['content']
        except TypeError:
            raise validators.CriticalValidationError, gettext("No file was submitted. Check the encoding type on the form.")
        if not content:
            raise validators.CriticalValidationError, gettext("The submitted file is empty.")

    def render(self, data):
        return '<input type="file" id="%s" class="v%s" name="%s" />' % \
            (self.get_id(), self.__class__.__name__, self.field_name)

    def html2python(data):
        if data is None:
            raise EmptyValue
        return data
    html2python = staticmethod(html2python)

class ImageUploadField(FileUploadField):
    "A FileUploadField that raises CriticalValidationError if the uploaded file isn't an image."
    def __init__(self, *args, **kwargs):
        FileUploadField.__init__(self, *args, **kwargs)
        self.validator_list.insert(0, self.isValidImage)

    def isValidImage(self, field_data, all_data):
        try:
            validators.isValidImage(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

####################
# INTEGERS/FLOATS  #
####################

class IntegerField(TextField):
    def __init__(self, field_name, length=10, maxlength=None, is_required=False, validator_list=None, member_name=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isInteger] + validator_list
        if member_name is not None:
            self.member_name = member_name
        TextField.__init__(self, field_name, length, maxlength, is_required, validator_list)

    def isInteger(self, field_data, all_data):
        try:
            validators.isInteger(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

    def html2python(data):
        if data == '' or data is None:
            return None
        return int(data)
    html2python = staticmethod(html2python)

class SmallIntegerField(IntegerField):
    def __init__(self, field_name, length=5, maxlength=5, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isSmallInteger] + validator_list
        IntegerField.__init__(self, field_name, length, maxlength, is_required, validator_list)

    def isSmallInteger(self, field_data, all_data):
        if not -32768 <= int(field_data) <= 32767:
            raise validators.CriticalValidationError, gettext("Enter a whole number between -32,768 and 32,767.")

class PositiveIntegerField(IntegerField):
    def __init__(self, field_name, length=10, maxlength=None, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isPositive] + validator_list
        IntegerField.__init__(self, field_name, length, maxlength, is_required, validator_list)

    def isPositive(self, field_data, all_data):
        if int(field_data) < 0:
            raise validators.CriticalValidationError, gettext("Enter a positive number.")

class PositiveSmallIntegerField(IntegerField):
    def __init__(self, field_name, length=5, maxlength=None, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isPositiveSmall] + validator_list
        IntegerField.__init__(self, field_name, length, maxlength, is_required, validator_list)

    def isPositiveSmall(self, field_data, all_data):
        if not 0 <= int(field_data) <= 32767:
            raise validators.CriticalValidationError, gettext("Enter a whole number between 0 and 32,767.")

class FloatField(TextField):
    def __init__(self, field_name, max_digits, decimal_places, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        self.max_digits, self.decimal_places = max_digits, decimal_places
        validator_list = [self.isValidFloat] + validator_list
        TextField.__init__(self, field_name, max_digits+2, max_digits+2, is_required, validator_list)

    def isValidFloat(self, field_data, all_data):
        v = validators.IsValidFloat(self.max_digits, self.decimal_places)
        try:
            v(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

    def html2python(data):
        if data == '' or data is None:
            return None
        return float(data)
    html2python = staticmethod(html2python)

####################
# DATES AND TIMES  #
####################

class DatetimeField(TextField):
    """A FormField that automatically converts its data to a datetime.datetime object.
    The data should be in the format YYYY-MM-DD HH:MM:SS."""
    def __init__(self, field_name, length=30, maxlength=None, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        self.field_name = field_name
        self.length, self.maxlength = length, maxlength
        self.is_required = is_required
        self.validator_list = [validators.isValidANSIDatetime] + validator_list

    def html2python(data):
        "Converts the field into a datetime.datetime object"
        import datetime
        try:
            date, time = data.split()
            y, m, d = date.split('-')
            timebits = time.split(':')
            h, mn = timebits[:2]
            if len(timebits) > 2:
                s = int(timebits[2])
            else:
                s = 0
            return datetime.datetime(int(y), int(m), int(d), int(h), int(mn), s)
        except ValueError:
            return None
    html2python = staticmethod(html2python)

class DateField(TextField):
    """A FormField that automatically converts its data to a datetime.date object.
    The data should be in the format YYYY-MM-DD."""
    def __init__(self, field_name, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isValidDate] + validator_list
        TextField.__init__(self, field_name, length=10, maxlength=10,
            is_required=is_required, validator_list=validator_list)

    def isValidDate(self, field_data, all_data):
        try:
            validators.isValidANSIDate(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

    def html2python(data):
        "Converts the field into a datetime.date object"
        import time, datetime
        try:
            time_tuple = time.strptime(data, '%Y-%m-%d')
            return datetime.date(*time_tuple[0:3])
        except (ValueError, TypeError):
            return None
    html2python = staticmethod(html2python)

class TimeField(TextField):
    """A FormField that automatically converts its data to a datetime.time object.
    The data should be in the format HH:MM:SS or HH:MM:SS.mmmmmm."""
    def __init__(self, field_name, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isValidTime] + validator_list
        TextField.__init__(self, field_name, length=8, maxlength=8,
            is_required=is_required, validator_list=validator_list)

    def isValidTime(self, field_data, all_data):
        try:
            validators.isValidANSITime(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

    def html2python(data):
        "Converts the field into a datetime.time object"
        import time, datetime
        try:
            part_list = data.split('.')
            try:
                time_tuple = time.strptime(part_list[0], '%H:%M:%S')
            except ValueError: # seconds weren't provided
                time_tuple = time.strptime(part_list[0], '%H:%M')
            t = datetime.time(*time_tuple[3:6])
            if (len(part_list) == 2):
                t = t.replace(microsecond=int(part_list[1]))
            return t
        except (ValueError, TypeError, AttributeError):
            return None
    html2python = staticmethod(html2python)

####################
# INTERNET-RELATED #
####################

class EmailField(TextField):
    "A convenience FormField for validating e-mail addresses"
    def __init__(self, field_name, length=50, maxlength=75, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isValidEmail] + validator_list
        TextField.__init__(self, field_name, length, maxlength=maxlength,
            is_required=is_required, validator_list=validator_list)

    def isValidEmail(self, field_data, all_data):
        try:
            validators.isValidEmail(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

class URLField(TextField):
    "A convenience FormField for validating URLs"
    def __init__(self, field_name, length=50, maxlength=200, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isValidURL] + validator_list
        TextField.__init__(self, field_name, length=length, maxlength=maxlength,
            is_required=is_required, validator_list=validator_list)

    def isValidURL(self, field_data, all_data):
        try:
            validators.isValidURL(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

class IPAddressField(TextField):
    def __init__(self, field_name, length=15, maxlength=15, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isValidIPAddress] + validator_list
        TextField.__init__(self, field_name, length=length, maxlength=maxlength,
            is_required=is_required, validator_list=validator_list)

    def isValidIPAddress(self, field_data, all_data):
        try:
            validators.isValidIPAddress4(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

    def html2python(data):
        return data or None
    html2python = staticmethod(html2python)

####################
# MISCELLANEOUS    #
####################

class FilePathField(SelectField):
    "A SelectField whose choices are the files in a given directory."
    def __init__(self, field_name, path, match=None, recursive=False, is_required=False, validator_list=None):
        import os
        from django.db.models import BLANK_CHOICE_DASH
        if match is not None:
            import re
            match_re = re.compile(match)
        choices = not is_required and BLANK_CHOICE_DASH[:] or []
        if recursive:
            for root, dirs, files in os.walk(path):
                for f in files:
                    if match is None or match_re.search(f):
                        choices.append((os.path.join(root, f), f))
        else:
            try:
                for f in os.listdir(path):
                    full_file = os.path.join(path, f)
                    if os.path.isfile(full_file) and (match is None or match_re.search(f)):
                        choices.append((full_file, f))
            except OSError:
                pass
        SelectField.__init__(self, field_name, choices, 1, is_required, validator_list)

class PhoneNumberField(TextField):
    "A convenience FormField for validating phone numbers (e.g. '630-555-1234')"
    def __init__(self, field_name, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isValidPhone] + validator_list
        TextField.__init__(self, field_name, length=12, maxlength=12,
            is_required=is_required, validator_list=validator_list)

    def isValidPhone(self, field_data, all_data):
        try:
            validators.isValidPhone(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

class USStateField(TextField):
    "A convenience FormField for validating U.S. states (e.g. 'IL')"
    def __init__(self, field_name, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isValidUSState] + validator_list
        TextField.__init__(self, field_name, length=2, maxlength=2,
            is_required=is_required, validator_list=validator_list)

    def isValidUSState(self, field_data, all_data):
        try:
            validators.isValidUSState(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

    def html2python(data):
        return data.upper() # Should always be stored in upper case
    html2python = staticmethod(html2python)

class CommaSeparatedIntegerField(TextField):
    "A convenience FormField for validating comma-separated integer fields"
    def __init__(self, field_name, maxlength=None, is_required=False, validator_list=None):
        if validator_list is None: validator_list = []
        validator_list = [self.isCommaSeparatedIntegerList] + validator_list
        TextField.__init__(self, field_name, length=20, maxlength=maxlength,
            is_required=is_required, validator_list=validator_list)

    def isCommaSeparatedIntegerList(self, field_data, all_data):
        try:
            validators.isCommaSeparatedIntegerList(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages

    def render(self, data):
        if data is None:
            data = ''
        elif isinstance(data, (list, tuple)):
            data = ','.join(data)
        return super(CommaSeparatedIntegerField, self).render(data)

class RawIdAdminField(CommaSeparatedIntegerField):
    def html2python(data):
        if data:
            return data.split(',')
        else:
            return []
    html2python = staticmethod(html2python)

class XMLLargeTextField(LargeTextField):
    """
    A LargeTextField with an XML validator. The schema_path argument is the
    full path to a Relax NG compact schema to validate against.
    """
    def __init__(self, field_name, schema_path, **kwargs):
        self.schema_path = schema_path
        kwargs.setdefault('validator_list', []).insert(0, self.isValidXML)
        LargeTextField.__init__(self, field_name, **kwargs)

    def isValidXML(self, field_data, all_data):
        v = validators.RelaxNGCompact(self.schema_path)
        try:
            v(field_data, all_data)
        except validators.ValidationError, e:
            raise validators.CriticalValidationError, e.messages
