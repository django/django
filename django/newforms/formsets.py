from django import newforms as forms

# special field names
FORM_COUNT_FIELD_NAME = 'COUNT'
ORDERING_FIELD_NAME = 'ORDER'
DELETION_FIELD_NAME = 'DELETE'

def formset_for_form(form, num_extra=1, orderable=False, deletable=False):
    """Return a FormSet for the given form class."""
    attrs = {'form_class': form, 'num_extra': num_extra, 'orderable': orderable, 'deletable': deletable}
    return type(form.__name__ + 'FormSet', (BaseFormSet,), attrs)

class ManagementForm(forms.Form):
    """
    ``ManagementForm`` is used to keep track of how many form instances
    are displayed on the page. If adding new forms via javascript, you should
    increment the count field of this form as well.
    """
    def __init__(self, *args, **kwargs):
        self.base_fields[FORM_COUNT_FIELD_NAME] = forms.IntegerField(widget=forms.HiddenInput)
        super(ManagementForm, self).__init__(*args, **kwargs)

class BaseFormSet(object):
    """A collection of instances of the same Form class."""

    def __init__(self, data=None, auto_id='id_%s', prefix=None, initial=None):
        self.is_bound = data is not None
        self.prefix = prefix or 'form'
        self.auto_id = auto_id
        self.data = data
        self.initial = initial
        # initialization is different depending on whether we recieved data, initial, or nothing
        if data:
            self.management_form = ManagementForm(data, auto_id=self.auto_id, prefix=self.prefix)
            if self.management_form.is_valid():
                self.total_forms = self.management_form.clean_data[FORM_COUNT_FIELD_NAME]
                self.required_forms = self.total_forms - self.num_extra
            else:
                # not sure that ValidationError is the best thing to raise here
                raise forms.ValidationError('ManagementForm data is missing or has been tampered with')
        elif initial:
            self.required_forms = len(initial)
            self.total_forms = self.required_forms + self.num_extra
            self.management_form = ManagementForm(initial={FORM_COUNT_FIELD_NAME: self.total_forms}, auto_id=self.auto_id, prefix=self.prefix)
        else:
            self.required_forms = 0
            self.total_forms = self.num_extra
            self.management_form = ManagementForm(initial={FORM_COUNT_FIELD_NAME: self.total_forms}, auto_id=self.auto_id, prefix=self.prefix)

    def _get_form_list(self):
        """Return a list of Form instances."""
        if not hasattr(self, '_form_list'):
            self._form_list = []
            for i in range(0, self.total_forms):
                kwargs = {'data': self.data, 'auto_id': self.auto_id, 'prefix': self.add_prefix(i)}
                if self.initial and i < self.required_forms:
                     kwargs['initial'] = self.initial[i]
                form_instance = self.form_class(**kwargs)
                # HACK: if the form was not completed, replace it with a blank one
                if self.data and i >= self.required_forms and form_instance.is_empty():
                    form_instance = self.form_class(auto_id=self.auto_id, prefix=self.add_prefix(i))
                self.add_fields(form_instance, i)
                self._form_list.append(form_instance)
        return self._form_list

    form_list = property(_get_form_list)

    def full_clean(self):
        """
        Cleans all of self.data and populates self.__errors and self.clean_data.
        """
        is_valid = True
        
        errors = []
        if not self.is_bound: # Stop further processing.
            self.__errors = errors
            return
        clean_data = []
        deleted_data = []
        
        self._form_list = []
        # step backwards through the forms so when we hit the first filled one
        # we can easily require the rest without backtracking
        required = False
        for i in range(self.total_forms-1, -1, -1):
            kwargs = {'data': self.data, 'auto_id': self.auto_id, 'prefix': self.add_prefix(i)}
            
            # prep initial data if there is some
            if self.initial and i < self.required_forms:
                kwargs['initial'] = self.initial[i]
                
            # create the form instance
            form = self.form_class(**kwargs)
            self.add_fields(form, i)
            
            if self.data and (i < self.required_forms or not form.is_empty(exceptions=[ORDERING_FIELD_NAME])):
                required = True # forms cannot be empty anymore
            
            # HACK: if the form is empty and not required, replace it with a blank one
            # this is necessary to keep form.errors empty
            if not required and self.data and form.is_empty(exceptions=[ORDERING_FIELD_NAME]):
                form = self.form_class(auto_id=self.auto_id, prefix=self.add_prefix(i))
                self.add_fields(form, i)
            else:
                # if the formset is still vaild overall and this form instance
                # is valid, keep appending to clean_data
                if is_valid and form.is_valid():
                    if self.deletable and form.clean_data[DELETION_FIELD_NAME]:
                        deleted_data.append(form.clean_data)
                    else:
                        clean_data.append(form.clean_data)
                else:
                    is_valid = False
                # append to errors regardless
                errors.append(form.errors)
            self._form_list.append(form)

        deleted_data.reverse()
        if self.orderable:
            clean_data.sort(lambda x,y: x[ORDERING_FIELD_NAME] - y[ORDERING_FIELD_NAME])
        else:
            clean_data.reverse()
        errors.reverse()
        self._form_list.reverse()
        
        if is_valid:
            self.clean_data = clean_data
            self.deleted_data = deleted_data
        self.errors = errors
        self._is_valid = is_valid

        # TODO: user defined formset validation.
        
    def add_fields(self, form, index):
        """A hook for adding extra fields on to each form instance."""
        if self.orderable:
            form.fields[ORDERING_FIELD_NAME] = forms.IntegerField(label='Order', initial=index+1)
        if self.deletable:
            form.fields[DELETION_FIELD_NAME] = forms.BooleanField(label='Delete', required=False)

    def add_prefix(self, index):
        return '%s-%s' % (self.prefix, index)

    def is_valid(self):
        self.full_clean()
        return self._is_valid

# TODO: handle deletion and ordering in the same FormSet
# TODO: model integration: form_for_instance and form_for_model type functions
