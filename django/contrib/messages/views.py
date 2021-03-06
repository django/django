from django.contrib import messages


class SuccessMessageMixin:
    """
    Add a success message on successful form submission.
    """
    success_message = ''

    def form_valid(self, form):
        response = super().form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return response

    def get_success_message(self, cleaned_data):
        return self.success_message % cleaned_data


class SuccessDeleteMessageMixin:
    """
    Add a success message on a successful DELETE request (and sometimes POST request
    if this will make trigger delete).
    """
    success_message = ''

    def delete(self, *args, **kwargs):
        response = super().delete(*args, **kwargs)
        success_message = self.get_success_message()
        if success_message:
            messages.success(self.request, success_message)
        return response

    def get_success_message(self):
        return self.success_message
