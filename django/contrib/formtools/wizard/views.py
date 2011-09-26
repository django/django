import re

from django import forms
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.forms import formsets, ValidationError
from django.views.generic import TemplateView
from django.utils.datastructures import SortedDict
from django.utils.decorators import classonlymethod

from django.contrib.formtools.wizard.storage import get_storage
from django.contrib.formtools.wizard.storage.exceptions import NoFileStorageConfigured
from django.contrib.formtools.wizard.forms import ManagementForm


def normalize_name(name):
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
        return self._wizard.get_form_list().keys()

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
        This method is used within urls.py to create unique formwizard
        instances for every request. We need to override this method because
        we add some kwargs which are needed to make the formwizard usable.
        """
        initkwargs = cls.get_initkwargs(*args, **kwargs)
        return super(WizardView, cls).as_view(**initkwargs)

    @classmethod
    def get_initkwargs(cls, form_list, initial_dict=None,
            instance_dict=None, condition_dict=None, *args, **kwargs):
        """
        Creates a dict with all needed parameters for the form wizard instances.

        * `form_list` - is a list of forms. The list entries can be single form
          classes or tuples of (`step_name`, `form_class`). If you pass a list
          of forms, the formwizard will convert the class list to
          (`zero_based_counter`, `form_class`). This is needed to access the
          form for a specific step.
        * `initial_dict` - contains a dictionary of initial data dictionaries.
          The key should be equal to the `step_name` in the `form_list` (or
          the str of the zero based counter - if no step_names added in the
          `form_list`)
        * `instance_dict` - contains a dictionary of instance objects. This
          is only used when `ModelForm`s are used. The key should be equal to
          the `step_name` in the `form_list`. Same rules as for `initial_dict`
          apply.
        * `condition_dict` - contains a dictionary of boolean values or
          callables. If the value of for a specific `step_name` is callable it
          will be called with the formwizard instance as the only argument.
          If the return value is true, the step's form will be used.
        """
        kwargs.update({
            'initial_dict': initial_dict or {},
            'instance_dict': instance_dict or {},
            'condition_dict': condition_dict or {},
        })
        init_form_list = SortedDict()

        assert len(form_list) > 0, 'at least one form is needed'

        # walk through the passed form list
        for i, form in enumerate(form_list):
            if isinstance(form, (list, tuple)):
                # if the element is a tuple, add the tuple to the new created
                # sorted dictionary.
                init_form_list[unicode(form[0])] = form[1]
            else:
                # if not, add the form with a zero based counter as unicode
                init_form_list[unicode(i)] = form

        # walk through the new created list of forms
        for form in init_form_list.itervalues():
            if issubclass(form, formsets.BaseFormSet):
                # if the element is based on BaseFormSet (FormSet/ModelFormSet)
                # we need to override the form variable.
                form = form.form
            # check if any form contains a FileField, if yes, we need a
            # file_storage added to the formwizard (by subclassing).
            for field in form.base_fields.itervalues():
                if (isinstance(field, forms.FileField) and
                        not hasattr(cls, 'file_storage')):
                    raise NoFileStorageConfigured

        # build the kwargs for the formwizard instances
        kwargs['form_list'] = init_form_list
        return kwargs

    def get_wizard_name(self):
        return normalize_name(self.__class__.__name__)

    def get_prefix(self):
        # TODO: Add some kind of unique id to prefix
        return self.wizard_name

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
        form_list = SortedDict()
        for form_key, form_class in self.form_list.iteritems():
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
        # add the storage engine to the current formwizard instance
        self.wizard_name = self.get_wizard_name()
        self.prefix = self.get_prefix()
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
        # Look for a wizard_prev_step element in the posted data which
        # contains a valid step name. If one was found, render the requested
        # form. (This makes stepping back a lot easier).
        wizard_prev_step = self.request.POST.get('wizard_prev_step', None)
        if wizard_prev_step and wizard_prev_step in self.get_form_list():
            self.storage.current_step = wizard_prev_step
            form = self.get_form(
                data=self.storage.get_step_data(self.steps.current),
                files=self.storage.get_step_files(self.steps.current))
            return self.render(form)

        # Check if form was refreshed
        management_form = ManagementForm(self.request.POST, prefix=self.prefix)
        if not management_form.is_valid():
            raise ValidationError(
                'ManagementForm data is missing or has been tampered.')

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

    def render_done(self, form, **kwargs):
        """
        This method gets called when all forms passed. The method should also
        re-validate all steps to prevent manipulation. If any form don't
        validate, `render_revalidation_failure` should get called.
        If everything is fine call `done`.
        """
        final_form_list = []
        # walk through the form list and try to validate the data again.
        for form_key in self.get_form_list():
            form_obj = self.get_form(step=form_key,
                data=self.storage.get_step_data(form_key),
                files=self.storage.get_step_files(form_key))
            if not form_obj.is_valid():
                return self.render_revalidation_failure(form_key, form_obj, **kwargs)
            final_form_list.append(form_obj)

        # render the done view and reset the wizard before returning the
        # response. This is needed to prevent from rendering done with the
        # same data twice.
        done_response = self.done(final_form_list, **kwargs)
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
        as `initial`. If no initial data was provied while initializing the
        form wizard, a empty dictionary will be returned.
        """
        return self.initial_dict.get(step, {})

    def get_form_instance(self, step):
        """
        Returns a object which will be passed to the form for `step`
        as `instance`. If no instance object was provied while initializing
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
        # prepare the kwargs for the form instance.
        kwargs = self.get_form_kwargs(step)
        kwargs.update({
            'data': data,
            'files': files,
            'prefix': self.get_form_prefix(step, self.form_list[step]),
            'initial': self.get_form_initial(step),
        })
        if issubclass(self.form_list[step], forms.ModelForm):
            # If the form is based on ModelForm, add instance if available.
            kwargs.update({'instance': self.get_form_instance(step)})
        elif issubclass(self.form_list[step], forms.models.BaseModelFormSet):
            # If the form is based on ModelFormSet, add queryset if available.
            kwargs.update({'queryset': self.get_form_instance(step)})
        return self.form_list[step](**kwargs)

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
        If a step contains a `FormSet`, the key will be prefixed with formset
        and contain a list of the formset cleaned_data dictionaries.
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
        cleaned data, the stored values are being revalidated through the
        form. If the data doesn't validate, None will be returned.
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
        key = form_list.keyOrder.index(step) + 1
        if len(form_list.keyOrder) > key:
            return form_list.keyOrder[key]
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
        key = form_list.keyOrder.index(step) - 1
        if key >= 0:
            return form_list.keyOrder[key]
        return None

    def get_step_index(self, step=None):
        """
        Returns the index for the given `step` name. If no step is given,
        the current step will be used to get the index.
        """
        if step is None:
            step = self.steps.current
        return self.get_form_list().keyOrder.index(step)

    def get_context_data(self, form, *args, **kwargs):
        """
        Returns the template context for a step. You can overwrite this method
        to add more data for all or some steps. This method returns a
        dictionary containing the rendered form step. Available template
        context variables are:

         * all extra data stored in the storage backend
         * `form` - form instance of the current step
         * `wizard` - the wizard instance itself

        Example:

        .. code-block:: python

            class MyWizard(FormWizard):
                def get_context_data(self, form, **kwargs):
                    context = super(MyWizard, self).get_context_data(form, **kwargs)
                    if self.steps.current == 'my_step_name':
                        context.update({'another_var': True})
                    return context
        """
        context = super(WizardView, self).get_context_data(*args, **kwargs)
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
        context = self.get_context_data(form, **kwargs)
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
            next_step_url = reverse(self.url_name, kwargs={
                'step': self.steps.current,
            }) + query_string
            return redirect(next_step_url)

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
                files=self.storage.current_step_data,
            ), **kwargs)

        elif step_url in self.get_form_list():
            self.storage.current_step = step_url
            return self.render(self.get_form(
                data=self.storage.current_step_data,
                files=self.storage.current_step_data,
            ), **kwargs)

        # invalid step name, reset to first and redirect.
        else:
            self.storage.current_step = self.steps.first
            return redirect(self.url_name, step=self.steps.first)

    def post(self, *args, **kwargs):
        """
        Do a redirect if user presses the prev. step button. The rest of this
        is super'd from FormWizard.
        """
        prev_step = self.request.POST.get('wizard_prev_step', None)
        if prev_step and prev_step in self.get_form_list():
            self.storage.current_step = prev_step
            return redirect(self.url_name, step=prev_step)
        return super(NamedUrlWizardView, self).post(*args, **kwargs)

    def render_next_step(self, form, **kwargs):
        """
        When using the NamedUrlFormWizard, we have to redirect to update the
        browser's URL to match the shown step.
        """
        next_step = self.get_next_step()
        self.storage.current_step = next_step
        return redirect(self.url_name, step=next_step)

    def render_revalidation_failure(self, failed_step, form, **kwargs):
        """
        When a step fails, we have to redirect the user to the first failing
        step.
        """
        self.storage.current_step = failed_step
        return redirect(self.url_name, step=failed_step)

    def render_done(self, form, **kwargs):
        """
        When rendering the done view, we have to redirect first (if the URL
        name doesn't fit).
        """
        if kwargs.get('step', None) != self.done_step_name:
            return redirect(self.url_name, step=self.done_step_name)
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

