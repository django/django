"""
FormWizard class -- implements a multi-page form, validating between each
step and storing the form's state as HTML hidden fields so that no state is
stored on the server side.
"""

import cPickle as pickle

from django import forms
from django.conf import settings
from django.http import Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.hashcompat import md5_constructor

class FormWizard(object):
    # Dictionary of extra template context variables.
    extra_context = {}

    # The HTML (and POST data) field name for the "step" variable.
    step_field_name="wizard_step"

    # METHODS SUBCLASSES SHOULDN'T OVERRIDE ###################################

    def __init__(self, form_list, initial=None):
        "form_list should be a list of Form classes (not instances)."
        self.form_list = form_list[:]
        self.initial = initial or {}
        self.step = 0 # A zero-based counter keeping track of which step we're in.

    def __repr__(self):
        return "step: %d\nform_list: %s\ninitial_data: %s" % (self.step, self.form_list, self.initial)

    def get_form(self, step, data=None):
        "Helper method that returns the Form instance for the given step."
        return self.form_list[step](data, prefix=self.prefix_for_step(step), initial=self.initial.get(step, None))

    def num_steps(self):
        "Helper method that returns the number of steps."
        # You might think we should just set "self.form_list = len(form_list)"
        # in __init__(), but this calculation needs to be dynamic, because some
        # hook methods might alter self.form_list.
        return len(self.form_list)

    def __call__(self, request, *args, **kwargs):
        """
        Main method that does all the hard work, conforming to the Django view
        interface.
        """
        if 'extra_context' in kwargs:
            self.extra_context.update(kwargs['extra_context'])
        current_step = self.determine_step(request, *args, **kwargs)
        self.parse_params(request, *args, **kwargs)

        # Sanity check.
        if current_step >= self.num_steps():
            raise Http404('Step %s does not exist' % current_step)

        # For each previous step, verify the hash and process.
        # TODO: Move "hash_%d" to a method to make it configurable.
        for i in range(current_step):
            form = self.get_form(i, request.POST)
            if request.POST.get("hash_%d" % i, '') != self.security_hash(request, form):
                return self.render_hash_failure(request, i)
            self.process_step(request, form, i)

        # Process the current step. If it's valid, go to the next step or call
        # done(), depending on whether any steps remain.
        if request.method == 'POST':
            form = self.get_form(current_step, request.POST)
        else:
            form = self.get_form(current_step)
        if form.is_valid():
            self.process_step(request, form, current_step)
            next_step = current_step + 1

            # If this was the last step, validate all of the forms one more
            # time, as a sanity check, and call done().
            num = self.num_steps()
            if next_step == num:
                final_form_list = [self.get_form(i, request.POST) for i in range(num)]

                # Validate all the forms. If any of them fail validation, that
                # must mean the validator relied on some other input, such as
                # an external Web site.
                for i, f in enumerate(final_form_list):
                    if not f.is_valid():
                        return self.render_revalidation_failure(request, i, f)
                return self.done(request, final_form_list)

            # Otherwise, move along to the next step.
            else:
                form = self.get_form(next_step)
                current_step = next_step

        return self.render(form, request, current_step)

    def render(self, form, request, step, context=None):
        "Renders the given Form object, returning an HttpResponse."
        old_data = request.POST
        prev_fields = []
        if old_data:
            hidden = forms.HiddenInput()
            # Collect all data from previous steps and render it as HTML hidden fields.
            for i in range(step):
                old_form = self.get_form(i, old_data)
                hash_name = 'hash_%s' % i
                prev_fields.extend([bf.as_hidden() for bf in old_form])
                prev_fields.append(hidden.render(hash_name, old_data.get(hash_name, self.security_hash(request, old_form))))
        return self.render_template(request, form, ''.join(prev_fields), step, context)

    # METHODS SUBCLASSES MIGHT OVERRIDE IF APPROPRIATE ########################

    def prefix_for_step(self, step):
        "Given the step, returns a Form prefix to use."
        return str(step)

    def render_hash_failure(self, request, step):
        """
        Hook for rendering a template if a hash check failed.

        step is the step that failed. Any previous step is guaranteed to be
        valid.

        This default implementation simply renders the form for the given step,
        but subclasses may want to display an error message, etc.
        """
        return self.render(self.get_form(step), request, step, context={'wizard_error': 'We apologize, but your form has expired. Please continue filling out the form from this page.'})

    def render_revalidation_failure(self, request, step, form):
        """
        Hook for rendering a template if final revalidation failed.

        It is highly unlikely that this point would ever be reached, but See
        the comment in __call__() for an explanation.
        """
        return self.render(form, request, step)

    def security_hash(self, request, form):
        """
        Calculates the security hash for the given HttpRequest and Form instances.

        This creates a list of the form field names/values in a deterministic
        order, pickles the result with the SECRET_KEY setting and takes an md5
        hash of that.

        Subclasses may want to take into account request-specific information,
        such as the IP address.
        """
        data = [(bf.name, bf.data or '') for bf in form] + [settings.SECRET_KEY]
        # Use HIGHEST_PROTOCOL because it's the most efficient. It requires
        # Python 2.3, but Django requires 2.3 anyway, so that's OK.
        pickled = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
        return md5_constructor(pickled).hexdigest()

    def determine_step(self, request, *args, **kwargs):
        """
        Given the request object and whatever *args and **kwargs were passed to
        __call__(), returns the current step (which is zero-based).

        Note that the result should not be trusted. It may even be a completely
        invalid number. It's not the job of this method to validate it.
        """
        if not request.POST:
            return 0
        try:
            step = int(request.POST.get(self.step_field_name, 0))
        except ValueError:
            return 0
        return step

    def parse_params(self, request, *args, **kwargs):
        """
        Hook for setting some state, given the request object and whatever
        *args and **kwargs were passed to __call__(), sets some state.

        This is called at the beginning of __call__().
        """
        pass

    def get_template(self, step):
        """
        Hook for specifying the name of the template to use for a given step.

        Note that this can return a tuple of template names if you'd like to
        use the template system's select_template() hook.
        """
        return 'forms/wizard.html'

    def render_template(self, request, form, previous_fields, step, context=None):
        """
        Renders the template for the given step, returning an HttpResponse object.

        Override this method if you want to add a custom context, return a
        different MIME type, etc. If you only need to override the template
        name, use get_template() instead.

        The template will be rendered with the following context:
            step_field -- The name of the hidden field containing the step.
            step0      -- The current step (zero-based).
            step       -- The current step (one-based).
            step_count -- The total number of steps.
            form       -- The Form instance for the current step (either empty
                          or with errors).
            previous_fields -- A string representing every previous data field,
                          plus hashes for completed forms, all in the form of
                          hidden fields. Note that you'll need to run this
                          through the "safe" template filter, to prevent
                          auto-escaping, because it's raw HTML.
        """
        context = context or {}
        context.update(self.extra_context)
        return render_to_response(self.get_template(self.step), dict(context,
            step_field=self.step_field_name,
            step0=step,
            step=step + 1,
            step_count=self.num_steps(),
            form=form,
            previous_fields=previous_fields
        ), context_instance=RequestContext(request))

    def process_step(self, request, form, step):
        """
        Hook for modifying the FormWizard's internal state, given a fully
        validated Form object. The Form is guaranteed to have clean, valid
        data.

        This method should *not* modify any of that data. Rather, it might want
        to set self.extra_context or dynamically alter self.form_list, based on
        previously submitted forms.

        Note that this method is called every time a page is rendered for *all*
        submitted steps.
        """
        pass

    # METHODS SUBCLASSES MUST OVERRIDE ########################################

    def done(self, request, form_list):
        """
        Hook for doing something with the validated data. This is responsible
        for the final processing.

        form_list is a list of Form instances, each containing clean, valid
        data.
        """
        raise NotImplementedError("Your %s class has not defined a done() method, which is required." % self.__class__.__name__)
