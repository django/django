from django import newforms as forms

# special field names
FORM_COUNT_FIELD_NAME = 'COUNT'
ORDERING_FIELD_NAME = 'ORDER'
DELETION_FIELD_NAME = 'DELETE'

class ManagementForm(forms.Form):
    """
    ``ManagementForm`` is used to keep track of how many form instances
    are displayed on the page. If adding new forms via javascript, you should
    increment the count field of this form as well.
    """
    def __init__(self, *args, **kwargs):
        self.base_fields[FORM_COUNT_FIELD_NAME] = forms.IntegerField(widget=forms.HiddenInput)
        super(ManagementForm, self).__init__(*args, **kwargs)

class FormSet(object):
    """A collection of instances of the same Form class."""

    def __init__(self, form_class, data=None, auto_id='id_%s', prefix=None, initial=None):
        self.form_class = form_class
        self.prefix = prefix or 'form'
        self.auto_id = auto_id
        # initialization is different depending on whether we recieved data, initial, or nothing
        if data:
            self.management_form = ManagementForm(data, auto_id=self.auto_id, prefix=self.prefix)
            if self.management_form.is_valid():
                form_count = self.management_form.clean_data[FORM_COUNT_FIELD_NAME]
            else:
                # not sure that ValidationError is the best thing to raise here
                raise forms.ValidationError('ManagementForm data is missing or has been tampered with')
            self.form_list = self._forms_for_data(data, form_count=form_count)
        elif initial:
            form_count = len(initial)
            self.management_form = ManagementForm(initial={FORM_COUNT_FIELD_NAME: form_count+1}, auto_id=self.auto_id, prefix=self.prefix)
            self.form_list = self._forms_for_initial(initial, form_count=form_count)
        else:
            self.management_form = ManagementForm(initial={FORM_COUNT_FIELD_NAME: 1}, auto_id=self.auto_id, prefix=self.prefix)
            self.form_list = self._empty_forms(form_count=1)

    # TODO: initialization needs some cleanup and some restructuring
    # TODO: allow more than 1 extra blank form to be displayed

    def _forms_for_data(self, data, form_count):
        form_list = []
        for i in range(0, form_count-1):
            form_instance = self.form_class(data, auto_id=self.auto_id, prefix=self.add_prefix(i))
            self.add_fields(form_instance, i)
            form_list.append(form_instance)
        # hackish, but if the last form stayed empty, replace it with a 
        # blank one. no 'data' or 'initial' arguments
        form_instance = self.form_class(data, auto_id=self.auto_id, prefix=self.add_prefix(form_count-1))
        if form_instance.is_empty():
            form_instance = self.form_class(auto_id=self.auto_id, prefix=self.add_prefix(form_count-1))
        self.add_fields(form_instance, form_count-1)
        form_list.append(form_instance)
        return form_list

    def _forms_for_initial(self, initial, form_count):
        form_list = []
        # generate a form for each item in initial, plus one empty one
        for i in range(0, form_count):
            form_instance = self.form_class(initial=initial[i], auto_id=self.auto_id, prefix=self.add_prefix(i))
            self.add_fields(form_instance, i)
            form_list.append(form_instance)
        # add 1 empty form
        form_instance = self.form_class(auto_id=self.auto_id, prefix=self.add_prefix(i+1))
        self.add_fields(form_instance, i+1)
        form_list.append(form_instance)
        return form_list

    def _empty_forms(self, form_count):
        form_list = []
        # we only need one form, there's no inital data and no post data
        form_instance = self.form_class(auto_id=self.auto_id, prefix=self.add_prefix(0))
        form_list.append(form_instance)
        return form_list

    def get_forms(self):
        return self.form_list

    def add_fields(self, form, index):
        """A hook for adding extra fields on to each form instance."""
        pass

    def add_prefix(self, index):
        return '%s-%s' % (self.prefix, index)

    def _get_clean_data(self):
        return self.get_clean_data()

    def get_clean_data(self):
        clean_data_list = []
        for form in self.get_non_empty_forms():
            clean_data_list.append(form.clean_data)
        return clean_data_list

    clean_data = property(_get_clean_data)

    def is_valid(self):
        for form in self.get_non_empty_forms():
            if not form.is_valid():
                return False
        return True

    def get_non_empty_forms(self):
        """Return all forms that aren't empty."""
        return [form for form in self.form_list if not form.is_empty()]

class FormSetWithDeletion(FormSet):
    """A ``FormSet`` that handles deletion of forms."""

    def add_fields(self, form, index):
        """Add a delete checkbox to each form."""
        form.fields[DELETION_FIELD_NAME] = forms.BooleanField(label='Delete', required=False)

    def get_clean_data(self):
        self.deleted_data = []
        clean_data_list = []
        for form in self.get_non_empty_forms():
            if form.clean_data[DELETION_FIELD_NAME]:
                # stick data marked for deletetion in self.deleted_data
                self.deleted_data.append(form.clean_data)
            else:
               clean_data_list.append(form.clean_data)
        return clean_data_list

class FormSetWithOrdering(FormSet):
    """A ``FormSet`` that handles re-ordering of forms."""

    def get_non_empty_forms(self):
        return [form for form in self.form_list if not form.is_empty(exceptions=[ORDERING_FIELD_NAME])]

    def add_fields(self, form, index):
        """Add an ordering field to each form."""
        form.fields[ORDERING_FIELD_NAME] = forms.IntegerField(label='Order', initial=index+1)

    def get_clean_data(self):
        clean_data_list = []
        for form in self.get_non_empty_forms():
            clean_data_list.append(form.clean_data)
        # sort clean_data by the 'ORDER' field
        clean_data_list.sort(lambda x,y: x[ORDERING_FIELD_NAME] - y[ORDERING_FIELD_NAME])
        return clean_data_list

    def is_valid(self):
        for form in self.get_non_empty_forms():
            if not form.is_valid():
                return False
        return True

# TODO: handle deletion and ordering in the same FormSet
# TODO: model integration: form_for_instance and form_for_model type functions
