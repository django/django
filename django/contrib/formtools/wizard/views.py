from collections import OrderedDict
import re

from django import forms
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.forms import formsets, ValidationError
from django.views.generic import TemplateView
from django.utils.decorators import classonlymethod
from django.utils.translation import ugettext as _
from django.utils import six

from django.contrib.formtools.wizard.storage import get_storage
from django.contrib.formtools.wizard.storage.exceptions import NoFileStorageConfigured
from django.contrib.formtools.wizard.forms import ManagementForm


def normalize_name(name):
    """
    Converts camel-case style names into underscore separated words. Example::

        >>> normalize_name('oneTwoThree')
        'one_two_three'
        >>> normalize_name('FourFiveSix')
        'four_five_six'

    """
    new = re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', '_\\1', name)
    return new.lower().strip('_')


class StepsHelper(object):

    def __init__(self, wizard):
        self._wizard = wizard

    def __dir__(self):
        return self.all

    def __len__(self):
        return self.count

    def __repr__(self):
        return '<StepsHelper for %s (steps: %s)>' % (self._wizard, self.all)

    @property
    def all(self):
        "Returns the names of all steps/forms."
        return list(self._wizard.get_form_list())

    @property
    def count(self):
        "Returns the total number of steps/forms in this the wizard."
        return len(self.all)

    @property
    def current(self):
        """
        Returns the current step. If no current step is stored in the
        storage backend, the first step will be returned.
        """
        return self._wizard.storage.current_step or self.first

    @property
    def first(self):
        "Returns the name of the first step."
        return self.all[0]

    @property
    def last(self):
        "Returns the name of the last step."
        return self.all[-1]

    @property
    def next(self):
        "Returns the next step."
        return self._wizard.get_next_step()

    @property
    def prev(self):
        "Returns the previous step."
        return self._wizard.get_prev_step()

    @property
    def index(self):
        "Returns the index for the current step."
        return self._wizard.get_step_index()

    @property
    def step0(self):
        return int(self.index)

    @property
    def step1(self):
        return int(self.index) + 1


class WizardView(TemplateView):
    """
    The WizardView is used to create multi-page forms and handles all the
    storage and validation stuff. The wizard is based on Django's generic
    class based views.
    """
    storage_name = None
    form_list = None
    initial_dict = None
    instance_dict = None
    condition_dict = None
    template_name = 'formtools/wizard/wizard_form.html'

    def __repr__(self):
        return '<%s: forms: %s>' % (self.__class__.__name__, self.form_list)

    @classonlymethod
    def as_view(cls, *args, **kwargs):
        """
        This method is used within urls.py to create unique wizardview
        instances for every request. We need to override this method because
        we add some kwargs which are needed to make the wizardview usable.
        """
        initkwargs = cls.get_initkwargs(*args, **kwargs)
        return super(WizardView, cls).as_view(**initkwargs)

    @classmethod
    def get_initkwargs(cls, form_list=None, initial_dict=None,
            instance_dict=None, condition_dict=None, *args, **kwargs):
        """
        Creates a dict with all needed parameters for the form wizard instances.

        * `form_list` - is a list of forms. The list entries can be single form
          classes or tuples of (`step_name`, `form_class`). If you pass a list
          of forms, the wizardview will convert the class list to
          (`zero_based_counter`, `form_class`). This is needed to access the
          form for a specific step.
        * `initial_dict` - contains a dictionary of initial data dictionaries.
          The key should be equal to the `step_name` in the `form_list` (or
          the str of the zero based counter - if no step_names added in the
          `form_list`)
        * `instance_dict` - contains a dictionary whose values are model
          instances if the step is based on a ``ModelForm`` and querysets if
          the step is based on a ``ModelFormSet``. The key should be equal to
          the `step_name` in the `form_list`. Same rules as for `initial_dict`
          apply.
        * `condition_dict` - contains a dictionary of boolean values or
          callables. If the value of for a specific `step_name` is callable it
          will be called with the wizardview instance as the only argument.
          If the return value is true, the step's form will be used.
        """

        kwargs.update({
            'initial_dict': initial_dict or kwargs.pop('initial_dict',
                getattr(cls, 'initial_dict', None)) or {},
            'instance_dict': instance_dict or kwargs.pop('instance_dict',
                getattr(cls, 'instance_dict', None)) or {},
            'condition_dict': condition_dict or kwargs.pop('condition_dict',
                getattr(cls, 'condition_dict', None)) or {}
        })

        form_list = form_list or kwargs.pop('form_list',
            getattr(cls, 'form_list', None)) or []

        computed_form_list = OrderedDict()

        assert len(form_list) > 0, 'at least one form is needed'

        # walk through the passed form list
        for i, form in enumerate(form_list):
            if isinstance(form, (list, tuple)):
                # if the element is a tuple, add the tuple to the new created
                # sorted dictionary.
                computed_form_list[six.text_type(form[0])] = form[1]
            else:
                # if not, add the form with a zero based counter as unicode
                computed_form_list[six.text_type(i)] = form

        # walk through the new created list of forms
        for form in six.itervalues(computed_form_list):
            if issubclass(form, formsets.BaseFormSet):
                # if the element is based on BaseFormSet (FormSet/ModelFormSet)
                # we need to override the form variable.
                form = form.form
            # check if any form contains a FileField, if yes, we need a
            # file_storage added to the wizardview (by subclassing).
            for field in six.itervalues(form.base_fields):
                if (isinstance(field, forms.FileField) and
                        not hasattr(cls, 'file_storage')):
                    raise NoFileStorageConfigured(
                        "You need to define 'file_storage' in your "
                        "wizard view in order to handle file uploads.")

        # build the kwargs for the wizardview instances
        kwargs['form_list'] = computed_form_list
        return kwargs

    def get_prefix(self, *args, **kwargs):
        # TODO: Add some kind of unique id to prefix
        return normalize_name(self.__class__.__name__)

    def get_form_list(self):
        """
        This method returns a form_list based on the initial form list but
        checks if there is a condition method/value in the condition_list.
        If an entry exists in the condition list, it will call/read the value
        and respect the result. (True means add the form, False means ignore
        the form)

        The form_list is always generated on the fly because condition methods
        could use data from other (maybe previous forms).
        """
        form_list = OrderedDict()
        for form_key, form_class in six.iteritems(self.form_list):
            # try to fetch the value from condition list, by default, the form
            # gets passed to the new list.
            condition = self.condition_dict.get(form_key, True)
            if callable(condition):
                # call the value if needed, passes the current instance.
                condition = condition(self)
            if condition:
                form_list[form_key] = form_class
        return form_list

    def dispatch(self, request, *args, **kwargs):
        """
        This method gets called by the routing engine. The first argument is
        `request` which contains a `HttpRequest` instance.
        The request is stored in `self.request` for later use. The storage
        instance is stored in `self.storage`.

        After processing the request using the `dispatch` method, the
        response gets updated by the storage engine (for example add cookies).
        """
        # add the storage engine to the current wizardview instance
        self.prefix = self.get_prefix(*args, **kwargs)
        self.storage = get_storage(self.storage_name, self.prefix, request,
            getattr(self, 'file_storage', None))
        self.steps = StepsHelper(self)
        response = super(WizardView, self).dispatch(request, *args, **kwargs)

        # update the response (e.g. adding cookies)
        self.storage.update_response(response)
        return response

    def get(self, request, *args, **kwargs):
        """
        This method handles GET requests.

        If a GET request reaches this point, the wizard assumes that the user
        just starts at the first step or wants to restart the process.
        The data of the wizard will be resetted before rendering the first step.
        """
        self.storage.reset()

        # reset the current step to the first step.
        self.storage.current_step = self.steps.first
        return self.render(self.get_form())

    def post(self, *args, **kwargs):
        """
        This method handles POST requests.

        The wizard will render either the current step (if form validation
        wasn't successful), the next step (if the current step was stored
        successful) or the done view (if no more steps are available)
        """
        # Look for a wizard_goto_step element in the posted data which
        # contains a valid step name. If one was found, render the requested
        # form. (This makes stepping back a lot easier).
        wizard_goto_step = self.request.POST.get('wizard_goto_step', None)
        if wizard_goto_step and wizard_goto_step in self.get_form_list():
            return self.render_goto_step(wizard_goto_step)

        # Check if form was refreshed
        management_form = ManagementForm(self.request.POST, prefix=self.prefix)
        if not management_form.is_valid():
            raise ValidationError(
                _('ManagementForm data is missing or has been tampered.'),
                code='missing_management_form',
            )

        form_current_step = management_form.cleaned_data['current_step']
        if (form_current_step != self.steps.current and
                self.storage.current_step is not None):
            # form refreshed, change current step
            self.storage.current_step = form_current_step

        # get the form for the current step
        form = self.get_form(data=self.request.POST, files=self.request.FILES)

        # and try to validate
        if form.is_valid():
            # if the form is valid, store the cleaned data and files.
            self.storage.set_step_data(self.steps.current, self.process_step(form))
            self.storage.set_step_files(self.steps.current, self.process_step_files(form))

            # check if the current step is the last step
            if self.steps.current == self.steps.last:
                # no more steps, render done view
                return self.render_done(form, **kwargs)
            else:
                # proceed to the next step
                return self.render_next_step(form)
        return self.render(form)

    def render_next_step(self, form, **kwargs):
        """
        This method gets called when the next step/form should be rendered.
        `form` contains the last/current form.
        """
        # get the form instance based on the data from the storage backend
        # (if available).
        next_step = self.steps.next
        new_form = self.get_form(next_step,
            data=self.storage.get_step_data(next_step),
            files=self.storage.get_step_files(next_step))

        # change the stored current step
        self.storage.current_step = next_step
        return self.render(new_form, **kwargs)

    def render_goto_step(self, goto_step, **kwargs):
        """
        This method gets called when the current step has to be changed.
        `goto_step` contains the requested step to go to.
        """
        self.storage.current_step = goto_step
        form = self.get_form(
            data=self.storage.get_step_data(self.steps.current),
            files=self.storage.get_step_files(self.steps.current))
        return self.render(form)

    def render_done(self, form, **kwargs):
        """
        This method gets called when all forms passed. The method should also
        re-validate all steps to prevent manipulation. If any form fails to
        validate, `render_revalidation_failure` should get called.
        If everything is fine call `done`.
        """
        final_forms = OrderedDict()
        # walk through the form list and try to validate the data again.
        for form_key in self.get_form_list():
            form_obj = self.get_form(step=form_key,
                data=self.storage.get_step_data(form_key),
                files=self.storage.get_step_files(form_key))
            if not form_obj.is_valid():
                return self.render_revalidation_failure(form_key, form_obj, **kwargs)
            final_forms[form_key] = form_obj

        # render the done view and reset the wizard before returning the
        # response. This is needed to prevent from rendering done with the
        # same data twice.
        done_response = self.done(final_forms.values(), form_dict=final_forms, **kwargs)
        self.storage.reset()
        return done_response

    def get_form_prefix(self, step=None, form=None):
        """
        Returns the prefix which will be used when calling the actual form for
        the given step. `step` contains the step-name, `form` the form which
        will be called with the returned prefix.

        If no step is given, the form_prefix will determine the current step
        automatically.
        """
        if step is None:
            step = self.steps.current
        return str(step)

    def get_form_initial(self, step):
        """
        Returns a dictionary which will be passed to the form for `step`
        as `initial`. If no initial data was provided while initializing the
        form wizard, an empty dictionary will be returned.
        """
        return self.initial_dict.get(step, {})

    def get_form_instance(self, step):
        """
        Returns an object which will be passed to the form for `step`
        as `instance`. If no instance object was provided while initializing
        the form wizard, None will be returned.
        """
        return self.instance_dict.get(step, None)

    def get_form_kwargs(self, step=None):
        """
        Returns the keyword arguments for instantiating the form
        (or formset) on the given step.
        """
        return {}

    def get_form(self, step=None, data=None, files=None):
        """
        Constructs the form for a given `step`. If no `step` is defined, the
        current step will be determined automatically.

        The form will be initialized using the `data` argument to prefill the
        new form. If needed, instance or queryset (for `ModelForm` or
        `ModelFormSet`) will be added too.
        """
        if step is None:
            step = self.steps.current
        form_class = self.form_list[step]
        # prepare the kwargs for the form instance.
        kwargs = self.get_form_kwargs(step)
        kwargs.update({
            'data': data,
            'files': files,
            'prefix': self.get_form_prefix(step, form_class),
            'initial': self.get_form_initial(step),
        })
        if issubclass(form_class, (forms.ModelForm, forms.models.BaseInlineFormSet)):
            # If the form is based on ModelForm or InlineFormSet,
            # add instance if available and not previously set.
            kwargs.setdefault('instance', self.get_form_instance(step))
        elif issubclass(form_class, forms.models.BaseModelFormSet):
            # If the form is based on ModelFormSet, add queryset if available
            # and not previous set.
            kwargs.setdefault('queryset', self.get_form_instance(step))
        return form_class(**kwargs)

    def process_step(self, form):
        """
        This method is used to postprocess the form data. By default, it
        returns the raw `form.data` dictionary.
        """
        return self.get_form_step_data(form)

    def process_step_files(self, form):
        """
        This method is used to postprocess the form files. By default, it
        returns the raw `form.files` dictionary.
        """
        return self.get_form_step_files(form)

    def render_revalidation_failure(self, step, form, **kwargs):
        """
        Gets called when a form doesn't validate when rendering the done
        view. By default, it changes the current step to failing forms step
        and renders the form.
        """
        self.storage.current_step = step
        return self.render(form, **kwargs)

    def get_form_step_data(self, form):
        """
        Is used to return the raw form data. You may use this method to
        manipulate the data.
        """
        return form.data

    def get_form_step_files(self, form):
        """
        Is used to return the raw form files. You may use this method to
        manipulate the data.
        """
        return form.files

    def get_all_cleaned_data(self):
        """
        Returns a merged dictionary of all step cleaned_data dictionaries.
        If a step contains a `FormSet`, the key will be prefixed with
        'formset-' and contain a list of the formset cleaned_data dictionaries.
        """
        cleaned_data = {}
        for form_key in self.get_form_list():
            form_obj = self.get_form(
                step=form_key,
                data=self.storage.get_step_data(form_key),
                files=self.storage.get_step_files(form_key)
            )
            if form_obj.is_valid():
                if isinstance(form_obj.cleaned_data, (tuple, list)):
                    cleaned_data.update({
                        'formset-%s' % form_key: form_obj.cleaned_data
                    })
                else:
                    cleaned_data.update(form_obj.cleaned_data)
        return cleaned_data

    def get_cleaned_data_for_step(self, step):
        """
        Returns the cleaned data for a given `step`. Before returning the
        cleaned data, the stored values are revalidated through the form.
        If the data doesn't validate, None will be returned.
        """
        if step in self.form_list:
            form_obj = self.get_form(step=step,
                data=self.storage.get_step_data(step),
                files=self.storage.get_step_files(step))
            if form_obj.is_valid():
                return form_obj.cleaned_data
        return None

    def get_next_step(self, step=None):
        """
        Returns the next step after the given `step`. If no more steps are
        available, None will be returned. If the `step` argument is None, the
        current step will be determined automatically.
        """
        if step is None:
            step = self.steps.current
        form_list = self.get_form_list()
        keys = list(form_list.keys())
        key = keys.index(step) + 1
        if len(keys) > key:
            return keys[key]
        return None

    def get_prev_step(self, step=None):
        """
        Returns the previous step before the given `step`. If there are no
        steps available, None will be returned. If the `step` argument is
        None, the current step will be determined automatically.
        """
        if step is None:
            step = self.steps.current
        form_list = self.get_form_list()
        keys = list(form_list.keys())
        key = keys.index(step) - 1
        if key >= 0:
            return keys[key]
        return None

    def get_step_index(self, step=None):
        """
        Returns the index for the given `step` name. If no step is given,
        the current step will be used to get the index.
        """
        if step is None:
            step = self.steps.current
        return list(self.get_form_list().keys()).index(step)

    def get_context_data(self, form, **kwargs):
        """
        Returns the template context for a step. You can overwrite this method
        to add more data for all or some steps. This method returns a
        dictionary containing the rendered form step. Available template
        context variables are:

         * all extra data stored in the storage backend
         * `wizard` - a dictionary representation of the wizard instance

        Example:

        .. code-block:: python

            class MyWizard(WizardView):
                def get_context_data(self, form, **kwargs):
                    context = super(MyWizard, self).get_context_data(form=form, **kwargs)
                    if self.steps.current == 'my_step_name':
                        context.update({'another_var': True})
                    return context
        """
        context = super(WizardView, self).get_context_data(form=form, **kwargs)
        context.update(self.storage.extra_data)
        context['wizard'] = {
            'form': form,
            'steps': self.steps,
            'management_form': ManagementForm(prefix=self.prefix, initial={
                'current_step': self.steps.current,
            }),
        }
        return context

    def render(self, form=None, **kwargs):
        """
        Returns a ``HttpResponse`` containing all needed context data.
        """
        form = form or self.get_form()
        context = self.get_context_data(form=form, **kwargs)
        return self.render_to_response(context)

    def done(self, form_list, **kwargs):
        """
        This method must be overridden by a subclass to process to form data
        after processing all steps.
        """
        raise NotImplementedError("Your %s class has not defined a done() "
            "method, which is required." % self.__class__.__name__)


class SessionWizardView(WizardView):
    """
    A WizardView with pre-configured SessionStorage backend.
    """
    storage_name = 'django.contrib.formtools.wizard.storage.session.SessionStorage'


class CookieWizardView(WizardView):
    """
    A WizardView with pre-configured CookieStorage backend.
    """
    storage_name = 'django.contrib.formtools.wizard.storage.cookie.CookieStorage'


class NamedUrlWizardView(WizardView):
    """
    A WizardView with URL named steps support.
    """
    url_name = None
    done_step_name = None

    @classmethod
    def get_initkwargs(cls, *args, **kwargs):
        """
        We require a url_name to reverse URLs later. Additionally users can
        pass a done_step_name to change the URL name of the "done" view.
        """
        assert 'url_name' in kwargs, 'URL name is needed to resolve correct wizard URLs'
        extra_kwargs = {
            'done_step_name': kwargs.pop('done_step_name', 'done'),
            'url_name': kwargs.pop('url_name'),
        }
        initkwargs = super(NamedUrlWizardView, cls).get_initkwargs(*args, **kwargs)
        initkwargs.update(extra_kwargs)

        assert initkwargs['done_step_name'] not in initkwargs['form_list'], \
            'step name "%s" is reserved for "done" view' % initkwargs['done_step_name']
        return initkwargs

    def get_step_url(self, step):
        return reverse(self.url_name, kwargs={'step': step})

    def get(self, *args, **kwargs):
        """
        This renders the form or, if needed, does the http redirects.
        """
        step_url = kwargs.get('step', None)
        if step_url is None:
            if 'reset' in self.request.GET:
                self.storage.reset()
                self.storage.current_step = self.steps.first
            if self.request.GET:
                query_string = "?%s" % self.request.GET.urlencode()
            else:
                query_string = ""
            return redirect(self.get_step_url(self.steps.current)
                            + query_string)

        # is the current step the "done" name/view?
        elif step_url == self.done_step_name:
            last_step = self.steps.last
            return self.render_done(self.get_form(step=last_step,
                data=self.storage.get_step_data(last_step),
                files=self.storage.get_step_files(last_step)
            ), **kwargs)

        # is the url step name not equal to the step in the storage?
        # if yes, change the step in the storage (if name exists)
        elif step_url == self.steps.current:
            # URL step name and storage step name are equal, render!
            return self.render(self.get_form(
                data=self.storage.current_step_data,
                files=self.storage.current_step_files,
            ), **kwargs)

        elif step_url in self.get_form_list():
            self.storage.current_step = step_url
            return self.render(self.get_form(
                data=self.storage.current_step_data,
                files=self.storage.current_step_files,
            ), **kwargs)

        # invalid step name, reset to first and redirect.
        else:
            self.storage.current_step = self.steps.first
            return redirect(self.get_step_url(self.steps.first))

    def post(self, *args, **kwargs):
        """
        Do a redirect if user presses the prev. step button. The rest of this
        is super'd from WizardView.
        """
        wizard_goto_step = self.request.POST.get('wizard_goto_step', None)
        if wizard_goto_step and wizard_goto_step in self.get_form_list():
            return self.render_goto_step(wizard_goto_step)
        return super(NamedUrlWizardView, self).post(*args, **kwargs)

    def get_context_data(self, form, **kwargs):
        """
        NamedUrlWizardView provides the url_name of this wizard in the context
        dict `wizard`.
        """
        context = super(NamedUrlWizardView, self).get_context_data(form=form, **kwargs)
        context['wizard']['url_name'] = self.url_name
        return context

    def render_next_step(self, form, **kwargs):
        """
        When using the NamedUrlWizardView, we have to redirect to update the
        browser's URL to match the shown step.
        """
        next_step = self.get_next_step()
        self.storage.current_step = next_step
        return redirect(self.get_step_url(next_step))

    def render_goto_step(self, goto_step, **kwargs):
        """
        This method gets called when the current step has to be changed.
        `goto_step` contains the requested step to go to.
        """
        self.storage.current_step = goto_step
        return redirect(self.get_step_url(goto_step))

    def render_revalidation_failure(self, failed_step, form, **kwargs):
        """
        When a step fails, we have to redirect the user to the first failing
        step.
        """
        self.storage.current_step = failed_step
        return redirect(self.get_step_url(failed_step))

    def render_done(self, form, **kwargs):
        """
        When rendering the done view, we have to redirect first (if the URL
        name doesn't fit).
        """
        if kwargs.get('step', None) != self.done_step_name:
            return redirect(self.get_step_url(self.done_step_name))
        return super(NamedUrlWizardView, self).render_done(form, **kwargs)


class NamedUrlSessionWizardView(NamedUrlWizardView):
    """
    A NamedUrlWizardView with pre-configured SessionStorage backend.
    """
    storage_name = 'django.contrib.formtools.wizard.storage.session.SessionStorage'


class NamedUrlCookieWizardView(NamedUrlWizardView):
    """
    A NamedUrlFormWizard with pre-configured CookieStorageBackend.
    """
    storage_name = 'django.contrib.formtools.wizard.storage.cookie.CookieStorage'
