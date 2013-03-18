from django.views.generic.edit import FormMixin
from django.contrib import messages


class SuccessMessageMixin(FormMixin):
    """
    A mixin that add a success message when a form is completed
    """
    success_message = None

    def form_valid(self, form):
        success_message = self.get_success_message()
        if success_message:
            messages.success(self.request, success_message)
        return super(SuccessMessageMixin, self).form_valid(form)

    def get_success_message(self):
        if hasattr(self, 'object') and self.object:
            return self.success_message.format(object=self.object)
        return self.success_message
