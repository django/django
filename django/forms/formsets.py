from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ValidationError
from django.forms import Form
from django.forms.fields import IntegerField, BooleanField
from django.forms.util import ErrorList
from django.forms.widgets import HiddenInput
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils import six
from django.utils.six.moves import xrange
from django.utils.translation import ungettext, ugettext as _


__all__ = ('BaseFormSet', 'all_valid')

# special field names
TOTAL_FORM_COUNT = 'TOTAL_FORMS'
INITIAL_FORM_COUNT = 'INITIAL_FORMS'
MAX_NUM_FORM_COUNT = 'MAX_NUM_FORMS'
ORDERING_FIELD_NAME = 'ORDER'
DELETION_FIELD_NAME = 'DELETE'

# default maximum number of forms in a formset, to prevent memory exhaustion
DEFAULT_MAX_NUM = 1000

class ManagementForm(Form):
    """
    ``ManagementForm`` is used to keep track of how many form instances
    are displayed on the page. If adding new forms via javascript, you should
    increment the count field of this form as well.
    """
    def __init__(self, *args, **kwargs):
        self.base_fields[TOTAL_FORM_COUNT] = IntegerField(widget=HiddenInput)
        self.base_fields[INITIAL_FORM_COUNT] = IntegerField(widget=HiddenInput)
        # MAX_NUM_FORM_COUNT is output with the rest of the management form,
        # but only for the convenience of client-side code. The POST
        # value of MAX_NUM_FORM_COUNT returned from the client is not checked.
        self.base_fields[MAX_NUM_FORM_COUNT] = IntegerField(required=False, widget=HiddenInput)
        super(ManagementForm, self).__init__(*args, **kwargs)

@python_2_unicode_compatible
class BaseFormSet(object):
    """
    A collection of instances of the same Form class.
    """
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList):
        self.is_bound = data is not None or files is not None
        self.prefix = prefix or self.get_default_prefix()
        self.auto_id = auto_id
        self.data = data or {}
        self.files = files or {}
        self.initial = initial
        self.error_class = error_class
        self._errors = None
        self._non_form_errors = None

    def __str__(self):
        return self.as_table()

    def __iter__(self):
        """Yields the forms in the order they should be rendered"""
        return iter(self.forms)

    def __getitem__(self, index):
        """Returns the form at the given index, based on the rendering order"""
        return self.forms[index]

    def __len__(self):
        return len(self.forms)

    def __bool__(self):
        """All formsets have a management form which is not included in the length"""
        return True

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    @property
    def management_form(self):
        """Returns the ManagementForm instance for this FormSet."""
        if self.is_bound:
            form = ManagementForm(self.data, auto_id=self.auto_id, prefix=self.prefix)
            if not form.is_valid():
                raise ValidationError(
                    _('ManagementForm data is missing or has been tampered with'),
                    code='missing_management_form',
                )
        else:
            form = ManagementForm(auto_id=self.auto_id, prefix=self.prefix, initial={
                TOTAL_FORM_COUNT: self.total_form_count(),
                INITIAL_FORM_COUNT: self.initial_form_count(),
                MAX_NUM_FORM_COUNT: self.max_num
            })
        return form

    def total_form_count(self):
        """Returns the total number of forms in this FormSet."""
        if self.is_bound:
            # return absolute_max if it is lower than the actual total form
            # count in the data; this is DoS protection to prevent clients
            # from forcing the server to instantiate arbitrary numbers of
            # forms
            return min(self.management_form.cleaned_data[TOTAL_FORM_COUNT], self.absolute_max)
        else:
            initial_forms = self.initial_form_count()
            total_forms = initial_forms + self.extra
            # Allow all existing related objects/inlines to be displayed,
            # but don't allow extra beyond max_num.
            if initial_forms > self.max_num >= 0:
                total_forms = initial_forms
            elif total_forms > self.max_num >= 0:
                total_forms = self.max_num
        return total_forms

    def initial_form_count(self):
        """Returns the number of forms that are required in this FormSet."""
        if self.is_bound:
            return self.management_form.cleaned_data[INITIAL_FORM_COUNT]
        else:
            # Use the length of the initial data if it's there, 0 otherwise.
            initial_forms = len(self.initial) if self.initial else 0
        return initial_forms

    @cached_property
    def forms(self):
        """
        Instantiate forms at first property access.
        """
        # DoS protection is included in total_form_count()
        forms = [self._construct_form(i) for i in xrange(self.total_form_count())]
        return forms

    def _construct_form(self, i, **kwargs):
        """
        Instantiates and returns the i-th form instance in a formset.
        """
        defaults = {
            'auto_id': self.auto_id,
            'prefix': self.add_prefix(i),
            'error_class': self.error_class,
            }
        if self.is_bound:
            defaults['data'] = self.data
            defaults['files'] = self.files
        if self.initial and not 'initial' in kwargs:
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

    @property
    def initial_forms(self):
        """Return a list of all the initial forms in this formset."""
        return self.forms[:self.initial_form_count()]

    @property
    def extra_forms(self):
        """Return a list of all the extra forms in this formset."""
        return self.forms[self.initial_form_count():]

    @property
    def empty_form(self):
        form = self.form(
            auto_id=self.auto_id,
            prefix=self.add_prefix('__prefix__'),
            empty_permitted=True,
        )
        self.add_fields(form, None)
        return form

    @property
    def cleaned_data(self):
        """
        Returns a list of form.cleaned_data dicts for every form in self.forms.
        """
        if not self.is_valid():
            raise AttributeError("'%s' object has no attribute 'cleaned_data'" % self.__class__.__name__)
        return [form.cleaned_data for form in self.forms]

    @property
    def deleted_forms(self):
        """
        Returns a list of forms that have been marked for deletion.
        """
        if not self.is_valid() or not self.can_delete:
            return []
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

    @property
    def ordered_forms(self):
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
            # blank.
            def compare_ordering_key(k):
                if k[1] is None:
                    return (1, 0) # +infinity, larger than any number
                return (0, k[1])
            self._ordering.sort(key=compare_ordering_key)
        # Return a list of form.cleaned_data dicts in the order specified by
        # the form data.
        return [self.forms[i[0]] for i in self._ordering]

    @classmethod
    def get_default_prefix(cls):
        return 'form'

    def non_form_errors(self):
        """
        Returns an ErrorList of errors that aren't associated with a particular
        form -- i.e., from formset.clean(). Returns an empty ErrorList if there
        are none.
        """
        if self._non_form_errors is None:
            self.full_clean()
        return self._non_form_errors

    @property
    def errors(self):
        """
        Returns a list of form.errors for every form in self.forms.
        """
        if self._errors is None:
            self.full_clean()
        return self._errors

    def total_error_count(self):
        """
        Returns the number of errors across all forms in the formset.
        """
        return len(self.non_form_errors()) +\
            sum(len(form_errors) for form_errors in self.errors)

    def _should_delete_form(self, form):
        """
        Returns whether or not the form was marked for deletion.
        """
        return form.cleaned_data.get(DELETION_FIELD_NAME, False)

    def is_valid(self):
        """
        Returns True if every form in self.forms is valid.
        """
        if not self.is_bound:
            return False
        # We loop over every form.errors here rather than short circuiting on the
        # first failure to make sure validation gets triggered for every form.
        forms_valid = True
        err = self.errors
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if self.can_delete:
                if self._should_delete_form(form):
                    # This form is going to be deleted so any of its errors
                    # should not cause the entire formset to be invalid.
                    continue
            forms_valid &= form.is_valid()
        return forms_valid and not bool(self.non_form_errors())

    def full_clean(self):
        """
        Cleans all of self.data and populates self._errors and
        self._non_form_errors.
        """
        self._errors = []
        self._non_form_errors = self.error_class()

        if not self.is_bound: # Stop further processing.
            return
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            self._errors.append(form.errors)
        try:
            if (self.validate_max and
                self.total_form_count() - len(self.deleted_forms) > self.max_num) or \
                self.management_form.cleaned_data[TOTAL_FORM_COUNT] > self.absolute_max:
                raise ValidationError(ungettext(
                    "Please submit %d or fewer forms.",
                    "Please submit %d or fewer forms.", self.max_num) % self.max_num,
                    code='too_many_forms',
                )
            # Give self.clean() a chance to do cross-form validation.
            self.clean()
        except ValidationError as e:
            self._non_form_errors = self.error_class(e.messages)

    def clean(self):
        """
        Hook for doing any extra formset-wide cleaning after Form.clean() has
        been called on every form. Any ValidationError raised by this method
        will not be associated with a particular form; it will be accesible
        via formset.non_form_errors()
        """
        pass

    def has_changed(self):
        """
        Returns true if data in any form differs from initial.
        """
        return any(form.has_changed() for form in self)

    def add_fields(self, form, index):
        """A hook for adding extra fields on to each form instance."""
        if self.can_order:
            # Only pre-fill the ordering field for initial forms.
            if index is not None and index < self.initial_form_count():
                form.fields[ORDERING_FIELD_NAME] = IntegerField(label=_('Order'), initial=index+1, required=False)
            else:
                form.fields[ORDERING_FIELD_NAME] = IntegerField(label=_('Order'), required=False)
        if self.can_delete:
            form.fields[DELETION_FIELD_NAME] = BooleanField(label=_('Delete'), required=False)

    def add_prefix(self, index):
        return '%s-%s' % (self.prefix, index)

    def is_multipart(self):
        """
        Returns True if the formset needs to be multipart, i.e. it
        has FileInput. Otherwise, False.
        """
        if self.forms:
            return self.forms[0].is_multipart()
        else:
            return self.empty_form.is_multipart()

    @property
    def media(self):
        # All the forms on a FormSet are the same, so you only need to
        # interrogate the first form for media.
        if self.forms:
            return self.forms[0].media
        else:
            return self.empty_form.media

    def as_table(self):
        "Returns this formset rendered as HTML <tr>s -- excluding the <table></table>."
        # XXX: there is no semantic division between forms here, there
        # probably should be. It might make sense to render each form as a
        # table row with each field as a td.
        forms = ' '.join([form.as_table() for form in self])
        return mark_safe('\n'.join([six.text_type(self.management_form), forms]))

    def as_p(self):
        "Returns this formset rendered as HTML <p>s."
        forms = ' '.join([form.as_p() for form in self])
        return mark_safe('\n'.join([six.text_type(self.management_form), forms]))

    def as_ul(self):
        "Returns this formset rendered as HTML <li>s."
        forms = ' '.join([form.as_ul() for form in self])
        return mark_safe('\n'.join([six.text_type(self.management_form), forms]))

def formset_factory(form, formset=BaseFormSet, extra=1, can_order=False,
                    can_delete=False, max_num=None, validate_max=False):
    """Return a FormSet for the given form class."""
    if max_num is None:
        max_num = DEFAULT_MAX_NUM
    # hard limit on forms instantiated, to prevent memory-exhaustion attacks
    # limit is simply max_num + DEFAULT_MAX_NUM (which is 2*DEFAULT_MAX_NUM
    # if max_num is None in the first place)
    absolute_max = max_num + DEFAULT_MAX_NUM
    attrs = {'form': form, 'extra': extra,
             'can_order': can_order, 'can_delete': can_delete,
             'max_num': max_num, 'absolute_max': absolute_max,
             'validate_max' : validate_max}
    return type(form.__name__ + str('FormSet'), (formset,), attrs)

def all_valid(formsets):
    """Returns true if every formset in formsets is valid."""
    valid = True
    for formset in formsets:
        if not formset.is_valid():
            valid = False
    return valid
