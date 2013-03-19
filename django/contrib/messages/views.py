from django.views.generic.edit import FormMixin
from django.contrib import messages


class SuccessMessageMixin(FormMixin):
    """
    Adds a success message on successful form submission.
    """
    success_message = None

    def form_valid(self, form):
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return super(SuccessMessageMixin, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        return self.success_message % cleaned_data
