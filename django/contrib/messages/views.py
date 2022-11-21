from django.contrib import messages


class SuccessMessageMixin:
    """
    Add a success message on successful form submission.
    """

    success_message = ""

    def form_valid(self, form):
        response = super().form_valid(form)
        if success_message := self.get_success_message(form.cleaned_data):
            messages.success(self.request, success_message)
        return response

    def get_success_message(self, cleaned_data):
        return self.success_message % cleaned_data
