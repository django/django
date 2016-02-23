import warnings

from django.contrib import messages
from django.utils.deprecation import (
    PERCENT_PLACEHOLDER_RE, RemovedInDjango20Warning,
)


class SuccessMessageMixin(object):
    """
    Adds a success message on successful form submission.
    """
    success_message = ''

    def form_valid(self, form):
        response = super(SuccessMessageMixin, self).form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return response

    def get_success_message(self, cleaned_data):
        if PERCENT_PLACEHOLDER_RE.search(self.success_message):
            warnings.warn(
                'Legacy % placeholder syntax in success_message is deprecated. '
                'Use the Python str.format() syntax instead.',
                RemovedInDjango20Warning,
                stacklevel=2,
            )
            message = self.success_message % cleaned_data
        else:
            message = self.success_message.format(**cleaned_data)
        return message
