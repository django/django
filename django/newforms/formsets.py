from forms import Form, ValidationError
from fields import IntegerField, BooleanField
from widgets import HiddenInput, Media

__all__ = ('BaseFormSet', 'formset_for_form', 'all_valid')

# special field names
FORM_COUNT_FIELD_NAME = 'COUNT'
ORDERING_FIELD_NAME = 'ORDER'
DELETION_FIELD_NAME = 'DELETE'

class ManagementForm(Form):
    """
    ``ManagementForm`` is used to keep track of how many form instances
    are displayed on the page. If adding new forms via javascript, you should
    increment the count field of this form as well.
    """
    def __init__(self, *args, **kwargs):
        self.base_fields[FORM_COUNT_FIELD_NAME] = IntegerField(widget=HiddenInput)
        super(ManagementForm, self).__init__(*args, **kwargs)

class BaseFormSet(object):
    """A collection of instances of the same Form class."""

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, initial=None):
        self.is_bound = data is not None or files is not None
        self.prefix = prefix or 'form'
        self.auto_id = auto_id
        self.data = data
        self.files = files
        self.initial = initial
        # initialization is different depending on whether we recieved data, initial, or nothing
        if data or files:
            self.management_form = ManagementForm(data, files, auto_id=self.auto_id, prefix=self.prefix)
            if self.management_form.is_valid():
                self.total_forms = self.management_form.cleaned_data[FORM_COUNT_FIELD_NAME]
                self.required_forms = self.total_forms - self.num_extra
                self.change_form_count = self.total_forms - self.num_extra
            else:
                # not sure that ValidationError is the best thing to raise here
                raise ValidationError('ManagementForm data is missing or has been tampered with')
        elif initial:
            self.change_form_count = len(initial)
            self.required_forms = len(initial)
            self.total_forms = self.required_forms + self.num_extra
            self.management_form = ManagementForm(initial={FORM_COUNT_FIELD_NAME: self.total_forms}, auto_id=self.auto_id, prefix=self.prefix)
        else:
            self.change_form_count = 0
            self.required_forms = 0
            self.total_forms = self.num_extra
            self.management_form = ManagementForm(initial={FORM_COUNT_FIELD_NAME: self.total_forms}, auto_id=self.auto_id, prefix=self.prefix)

    def _get_add_forms(self):
        """Return a list of all the add forms in this ``FormSet``."""
        FormClass = self.form_class
        if not hasattr(self, '_add_forms'):
            add_forms = []
            for i in range(self.change_form_count, self.total_forms):
                kwargs = {'auto_id': self.auto_id, 'prefix': self.add_prefix(i)}
                if self.data:
                    kwargs['data'] = self.data
                if self.files:
                    kwargs['files'] = self.files
                add_form = FormClass(**kwargs)
                self.add_fields(add_form, i)
                add_forms.append(add_form)
            self._add_forms = add_forms
        return self._add_forms
    add_forms = property(_get_add_forms)

    def _get_change_forms(self):
        """Return a list of all the change forms in this ``FormSet``."""
        FormClass = self.form_class
        if not hasattr(self, '_change_forms'):
            change_forms = []
            for i in range(0, self.change_form_count):
                kwargs = {'auto_id': self.auto_id, 'prefix': self.add_prefix(i)}
                if self.data:
                    kwargs['data'] = self.data
                if self.files:
                    kwargs['files'] = self.files
                if self.initial:
                    kwargs['initial'] = self.initial[i]
                change_form = FormClass(**kwargs)
                self.add_fields(change_form, i)
                change_forms.append(change_form)
            self._change_forms= change_forms
        return self._change_forms
    change_forms = property(_get_change_forms)

    def _forms(self):
        return self.change_forms + self.add_forms
    forms = property(_forms)

    def full_clean(self):
        """Cleans all of self.data and populates self.__errors and self.cleaned_data."""
        is_valid = True
        errors = []
        if not self.is_bound: # Stop further processing.
            self.__errors = errors
            return
        cleaned_data = []
        deleted_data = []
        
        # Process change forms
        for form in self.change_forms:
            if form.is_valid():
                if self.deletable and form.cleaned_data[DELETION_FIELD_NAME]:
                    deleted_data.append(form.cleaned_data)
                else:
                    cleaned_data.append(form.cleaned_data)
            else:
                is_valid = False
            errors.append(form.errors)
        
        # Process add forms in reverse so we can easily tell when the remaining
        # ones should be required.
        required = False
        add_errors = []
        for i in range(len(self.add_forms)-1, -1, -1):
            form = self.add_forms[i]
            # If an add form is empty, reset it so it won't have any errors
            if form.is_empty([ORDERING_FIELD_NAME]) and not required:
                form.reset()
                continue
            else:
                required = True
                if form.is_valid():
                    cleaned_data.append(form.cleaned_data)
                else:
                    is_valid = False
            add_errors.append(form.errors)
        add_errors.reverse()
        errors.extend(add_errors)

        if self.orderable:
            cleaned_data.sort(lambda x,y: x[ORDERING_FIELD_NAME] - y[ORDERING_FIELD_NAME])

        if is_valid:
            self.cleaned_data = cleaned_data
            self.deleted_data = deleted_data
        self.errors = errors
        self._is_valid = is_valid

    def add_fields(self, form, index):
        """A hook for adding extra fields on to each form instance."""
        if self.orderable:
            form.fields[ORDERING_FIELD_NAME] = IntegerField(label='Order', initial=index+1)
        if self.deletable:
            form.fields[DELETION_FIELD_NAME] = BooleanField(label='Delete', required=False)

    def add_prefix(self, index):
        return '%s-%s' % (self.prefix, index)

    def is_valid(self):
        if not self.is_bound:
            return False
        self.full_clean()
        return self._is_valid

    def _get_media(self):
        # All the forms on a FormSet are the same, so you only need to 
        # interrogate the first form for media.
        if self.forms:
            return self.forms[0].media
        else:
            return Media()
    media = property(_get_media)
    
def formset_for_form(form, formset=BaseFormSet, num_extra=1, orderable=False, deletable=False):
    """Return a FormSet for the given form class."""
    attrs = {'form_class': form, 'num_extra': num_extra, 'orderable': orderable, 'deletable': deletable}
    return type(form.__name__ + 'FormSet', (formset,), attrs)

def all_valid(formsets):
    """Returns true if every formset in formsets is valid."""
    valid = True
    for formset in formsets:
        if not formset.is_valid():
            valid = False
    return valid
