"""
FormWizard class -- implements a multi-page form, validating between each
step and storing the form's state as HTML hidden fields so that no state is
stored on the server side.
"""
from django.forms import HiddenInput
from django.http import Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.crypto import constant_time_compare
from django.utils.translation import ugettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from django.contrib.formtools.utils import form_hmac

class FormWizard(object):
    # The HTML (and POST data) field name for the "step" variable.
    step_field_name="wizard_step"

    # METHODS SUBCLASSES SHOULDN'T OVERRIDE ###################################

    def __init__(self, form_list, initial=None):
        """
        Start a new wizard with a list of forms.

        form_list should be a list of Form classes (not instances).
        """
        self.form_list = form_list[:]
        self.initial = initial or {}

        # Dictionary of extra template context variables.
        self.extra_context = {}

        # A zero-based counter keeping track of which step we're in.
        self.step = 0

        import warnings
        warnings.warn(
            'Old-style form wizards have been deprecated; use the class-based '
            'views in django.contrib.formtools.wizard.views instead.',
            DeprecationWarning)

    def __repr__(self):
        return "step: %d\nform_list: %s\ninitial_data: %s" % (self.step, self.form_list, self.initial)

    def get_form(self, step, data=None):
        "Helper method that returns the Form instance for the given step."
        # Sanity check.
        if step >= self.num_steps():
            raise Http404('Step %s does not exist' % step)
        return self.form_list[step](data, prefix=self.prefix_for_step(step), initial=self.initial.get(step, None))

    def num_steps(self):
        "Helper method that returns the number of steps."
        # You might think we should just set "self.num_steps = len(form_list)"
        # in __init__(), but this calculation needs to be dynamic, because some
        # hook methods might alter self.form_list.
        return len(self.form_list)

    def _check_security_hash(self, token, request, form):
        expected = self.security_hash(request, form)
        return constant_time_compare(token, expected)

    @method_decorator(csrf_protect)
    def __call__(self, request, *args, **kwargs):
        """
        Main method that does all the hard work, conforming to the Django view
        interface.
        """
        if 'extra_context' in kwargs:
            self.extra_context.update(kwargs['extra_context'])
        current_step = self.get_current_or_first_step(request, *args, **kwargs)
        self.parse_params(request, *args, **kwargs)

        # Validate and process all the previous forms before instantiating the
        # current step's form in case self.process_step makes changes to
        # self.form_list.

        # If any of them fails validation, that must mean the validator relied
        # on some other input, such as an external Web site.

        # It is also possible that alidation might fail under certain attack
        # situations: an attacker might be able to bypass previous stages, and
        # generate correct security hashes for all the skipped stages by virtue
        # of:
        #  1) having filled out an identical form which doesn't have the
        #     validation (and does something different at the end),
        #  2) or having filled out a previous version of the same form which
        #     had some validation missing,
        #  3) or previously having filled out the form when they had more
        #     privileges than they do now.
        #
        # Since the hashes only take into account values, and not other other
        # validation the form might do, we must re-do validation now for
        # security reasons.
        previous_form_list = []
        for i in range(current_step):
            f = self.get_form(i, request.POST)
            if not self._check_security_hash(request.POST.get("hash_%d" % i, ''),
                                             request, f):
                return self.render_hash_failure(request, i)

            if not f.is_valid():
                return self.render_revalidation_failure(request, i, f)
            else:
                self.process_step(request, f, i)
                previous_form_list.append(f)

        # Process the current step. If it's valid, go to the next step or call
        # done(), depending on whether any steps remain.
        if request.method == 'POST':
            form = self.get_form(current_step, request.POST)
        else:
            form = self.get_form(current_step)

        if form.is_valid():
            self.process_step(request, form, current_step)
            next_step = current_step + 1

            if next_step == self.num_steps():
                return self.done(request, previous_form_list + [form])
            else:
                form = self.get_form(next_step)
                self.step = current_step = next_step

        return self.render(form, request, current_step)

    def render(self, form, request, step, context=None):
        "Renders the given Form object, returning an HttpResponse."
        old_data = request.POST
        prev_fields = []
        if old_data:
            hidden = HiddenInput()
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
        return self.render(self.get_form(step), request, step, context={'wizard_error': _('We apologize, but your form has expired. Please continue filling out the form from this page.')})

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

        Subclasses may want to take into account request-specific information,
        such as the IP address.
        """
        return form_hmac(form)

    def get_current_or_first_step(self, request, *args, **kwargs):
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
        return render_to_response(self.get_template(step), dict(context,
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
