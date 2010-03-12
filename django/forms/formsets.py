from forms import Form
from django.core.exceptions import ValidationError
from django.utils.encoding import StrAndUnicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from fields import IntegerField, BooleanField
from widgets import Media, HiddenInput
from util import ErrorList

__all__ = ('BaseFormSet', 'all_valid')

# special field names
TOTAL_FORM_COUNT = 'TOTAL_FORMS'
INITIAL_FORM_COUNT = 'INITIAL_FORMS'
MAX_NUM_FORM_COUNT = 'MAX_NUM_FORMS'
ORDERING_FIELD_NAME = 'ORDER'
DELETION_FIELD_NAME = 'DELETE'

class ManagementForm(Form):
    """
    ``ManagementForm`` is used to keep track of how many form instances
    are displayed on the page. If adding new forms via javascript, you should
    increment the count field of this form as well.
    """
    def __init__(self, *args, **kwargs):
        self.base_fields[TOTAL_FORM_COUNT] = IntegerField(widget=HiddenInput)
        self.base_fields[INITIAL_FORM_COUNT] = IntegerField(widget=HiddenInput)
        self.base_fields[MAX_NUM_FORM_COUNT] = IntegerField(widget=HiddenInput)
        super(ManagementForm, self).__init__(*args, **kwargs)

class BaseFormSet(StrAndUnicode):
    """
    A collection of instances of the same Form class.
    """
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList):
        self.is_bound = data is not None or files is not None
        self.prefix = prefix or self.get_default_prefix()
        self.auto_id = auto_id
        self.data = data
        self.files = files
        self.initial = initial
        self.error_class = error_class
        self._errors = None
        self._non_form_errors = None
        # construct the forms in the formset
        self._construct_forms()

    def __unicode__(self):
        return self.as_table()

    def _management_form(self):
        """Returns the ManagementForm instance for this FormSet."""
        if self.data or self.files:
            form = ManagementForm(self.data, auto_id=self.auto_id, prefix=self.prefix)
            if not form.is_valid():
                raise ValidationError('ManagementForm data is missing or has been tampered with')
        else:
            form = ManagementForm(auto_id=self.auto_id, prefix=self.prefix, initial={
                TOTAL_FORM_COUNT: self.total_form_count(),
                INITIAL_FORM_COUNT: self.initial_form_count(),
                MAX_NUM_FORM_COUNT: self.max_num
            })
        return form
    management_form = property(_management_form)

    def total_form_count(self):
        """Returns the total number of forms in this FormSet."""
        if self.data or self.files:
            return self.management_form.cleaned_data[TOTAL_FORM_COUNT]
        else:
            total_forms = self.initial_form_count() + self.extra
            if total_forms > self.max_num > 0:
                total_forms = self.max_num
        return total_forms

    def initial_form_count(self):
        """Returns the number of forms that are required in this FormSet."""
        if self.data or self.files:
            return self.management_form.cleaned_data[INITIAL_FORM_COUNT]
        else:
            # Use the length of the inital data if it's there, 0 otherwise.
            initial_forms = self.initial and len(self.initial) or 0
            if initial_forms > self.max_num > 0:
                initial_forms = self.max_num
        return initial_forms

    def _construct_forms(self):
        # instantiate all the forms and put them in self.forms
        self.forms = []
        for i in xrange(self.total_form_count()):
            self.forms.append(self._construct_form(i))

    def _construct_form(self, i, **kwargs):
        """
        Instantiates and returns the i-th form instance in a formset.
        """
        defaults = {'auto_id': self.auto_id, 'prefix': self.add_prefix(i)}
        if self.data or self.files:
            defaults['data'] = self.data
            defaults['files'] = self.files
        if self.initial:
            try:
                defaults['initial'] = self.initial[i]
            except IndexError:
                pass
        # Allow extra forms to be empty.
        if i >= self.initial_form_count():
            defaults['empty_permitted'] = True
        defaults.update(kwargs)
        form = self.form(**defaults)
        self.add_fields(form, i)
        return form

    def _get_initial_forms(self):
        """Return a list of all the initial forms in this formset."""
        return self.forms[:self.initial_form_count()]
    initial_forms = property(_get_initial_forms)

    def _get_extra_forms(self):
        """Return a list of all the extra forms in this formset."""
        return self.forms[self.initial_form_count():]
    extra_forms = property(_get_extra_forms)

    def _get_empty_form(self, **kwargs):
        defaults = {
            'auto_id': self.auto_id,
            'prefix': self.add_prefix('__prefix__'),
            'empty_permitted': True,
        }
        if self.data or self.files:
            defaults['data'] = self.data
            defaults['files'] = self.files
        defaults.update(kwargs)
        form = self.form(**defaults)
        self.add_fields(form, None)
        return form
    empty_form = property(_get_empty_form)

    # Maybe this should just go away?
    def _get_cleaned_data(self):
        """
        Returns a list of form.cleaned_data dicts for every form in self.forms.
        """
        if not self.is_valid():
            raise AttributeError("'%s' object has no attribute 'cleaned_data'" % self.__class__.__name__)
        return [form.cleaned_data for form in self.forms]
    cleaned_data = property(_get_cleaned_data)

    def _get_deleted_forms(self):
        """
        Returns a list of forms that have been marked for deletion. Raises an
        AttributeError if deletion is not allowed.
        """
        if not self.is_valid() or not self.can_delete:
            raise AttributeError("'%s' object has no attribute 'deleted_forms'" % self.__class__.__name__)
        # construct _deleted_form_indexes which is just a list of form indexes
        # that have had their deletion widget set to True
        if not hasattr(self, '_deleted_form_indexes'):
            self._deleted_form_indexes = []
            for i in range(0, self.total_form_count()):
                form = self.forms[i]
                # if this is an extra form and hasn't changed, don't consider it
                if i >= self.initial_form_count() and not form.has_changed():
                    continue
                if self._should_delete_form(form):
                    self._deleted_form_indexes.append(i)
        return [self.forms[i] for i in self._deleted_form_indexes]
    deleted_forms = property(_get_deleted_forms)

    def _get_ordered_forms(self):
        """
        Returns a list of form in the order specified by the incoming data.
        Raises an AttributeError if ordering is not allowed.
        """
        if not self.is_valid() or not self.can_order:
            raise AttributeError("'%s' object has no attribute 'ordered_forms'" % self.__class__.__name__)
        # Construct _ordering, which is a list of (form_index, order_field_value)
        # tuples. After constructing this list, we'll sort it by order_field_value
        # so we have a way to get to the form indexes in the order specified
        # by the form data.
        if not hasattr(self, '_ordering'):
            self._ordering = []
            for i in range(0, self.total_form_count()):
                form = self.forms[i]
                # if this is an extra form and hasn't changed, don't consider it
                if i >= self.initial_form_count() and not form.has_changed():
                    continue
                # don't add data marked for deletion to self.ordered_data
                if self.can_delete and self._should_delete_form(form):
                    continue
                self._ordering.append((i, form.cleaned_data[ORDERING_FIELD_NAME]))
            # After we're done populating self._ordering, sort it.
            # A sort function to order things numerically ascending, but
            # None should be sorted below anything else. Allowing None as
            # a comparison value makes it so we can leave ordering fields
            # blamk.
            def compare_ordering_values(x, y):
                if x[1] is None:
                    return 1
                if y[1] is None:
                    return -1
                return x[1] - y[1]
            self._ordering.sort(compare_ordering_values)
        # Return a list of form.cleaned_data dicts in the order spcified by
        # the form data.
        return [self.forms[i[0]] for i in self._ordering]
    ordered_forms = property(_get_ordered_forms)

    #@classmethod
    def get_default_prefix(cls):
        return 'form'
    get_default_prefix = classmethod(get_default_prefix)

    def non_form_errors(self):
        """
        Returns an ErrorList of errors that aren't associated with a particular
        form -- i.e., from formset.clean(). Returns an empty ErrorList if there
        are none.
        """
        if self._non_form_errors is not None:
            return self._non_form_errors
        return self.error_class()

    def _get_errors(self):
        """
        Returns a list of form.errors for every form in self.forms.
        """
        if self._errors is None:
            self.full_clean()
        return self._errors
    errors = property(_get_errors)

    def _should_delete_form(self, form):
        # The way we lookup the value of the deletion field here takes
        # more code than we'd like, but the form's cleaned_data will
        # not exist if the form is invalid.
        field = form.fields[DELETION_FIELD_NAME]
        raw_value = form._raw_value(DELETION_FIELD_NAME)
        should_delete = field.clean(raw_value)
        return should_delete

    def is_valid(self):
        """
        Returns True if form.errors is empty for every form in self.forms.
        """
        if not self.is_bound:
            return False
        # We loop over every form.errors here rather than short circuiting on the
        # first failure to make sure validation gets triggered for every form.
        forms_valid = True
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if self.can_delete:
                if self._should_delete_form(form):
                    # This form is going to be deleted so any of its errors
                    # should not cause the entire formset to be invalid.
                    continue
            if bool(self.errors[i]):
                forms_valid = False
        return forms_valid and not bool(self.non_form_errors())

    def full_clean(self):
        """
        Cleans all of self.data and populates self._errors.
        """
        self._errors = []
        if not self.is_bound: # Stop further processing.
            return
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            self._errors.append(form.errors)
        # Give self.clean() a chance to do cross-form validation.
        try:
            self.clean()
        except ValidationError, e:
            self._non_form_errors = self.error_class(e.messages)

    def clean(self):
        """
        Hook for doing any extra formset-wide cleaning after Form.clean() has
        been called on every form. Any ValidationError raised by this method
        will not be associated with a particular form; it will be accesible
        via formset.non_form_errors()
        """
        pass

    def add_fields(self, form, index):
        """A hook for adding extra fields on to each form instance."""
        if self.can_order:
            # Only pre-fill the ordering field for initial forms.
            if index is not None and index < self.initial_form_count():
                form.fields[ORDERING_FIELD_NAME] = IntegerField(label=_(u'Order'), initial=index+1, required=False)
            else:
                form.fields[ORDERING_FIELD_NAME] = IntegerField(label=_(u'Order'), required=False)
        if self.can_delete:
            form.fields[DELETION_FIELD_NAME] = BooleanField(label=_(u'Delete'), required=False)

    def add_prefix(self, index):
        return '%s-%s' % (self.prefix, index)

    def is_multipart(self):
        """
        Returns True if the formset needs to be multipart-encrypted, i.e. it
        has FileInput. Otherwise, False.
        """
        return self.forms and self.forms[0].is_multipart()

    def _get_media(self):
        # All the forms on a FormSet are the same, so you only need to
        # interrogate the first form for media.
        if self.forms:
            return self.forms[0].media
        else:
            return Media()
    media = property(_get_media)

    def as_table(self):
        "Returns this formset rendered as HTML <tr>s -- excluding the <table></table>."
        # XXX: there is no semantic division between forms here, there
        # probably should be. It might make sense to render each form as a
        # table row with each field as a td.
        forms = u' '.join([form.as_table() for form in self.forms])
        return mark_safe(u'\n'.join([unicode(self.management_form), forms]))

def formset_factory(form, formset=BaseFormSet, extra=1, can_order=False,
                    can_delete=False, max_num=0):
    """Return a FormSet for the given form class."""
    attrs = {'form': form, 'extra': extra,
             'can_order': can_order, 'can_delete': can_delete,
             'max_num': max_num}
    return type(form.__name__ + 'FormSet', (formset,), attrs)

def all_valid(formsets):
    """Returns true if every formset in formsets is valid."""
    valid = True
    for formset in formsets:
        if not formset.is_valid():
            valid = False
    return valid
