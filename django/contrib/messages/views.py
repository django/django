from types import FunctionType
from django.contrib import messages
from django.utils.functional import curry


class _MessageAPIWrapper(object):
    """
    Wrap the django.contrib.messages.api module to automatically pass a given
    request object as the first parameter of function calls.
    """
    API = {
        'add_message', 'get_messages',
        'get_level', 'set_level',
        'debug', 'info', 'success', 'warning', 'error',
    }
    def __init__(self, request):
        for name in self.API:
            api_fn = getattr(messages.api, name)
            setattr(self, method, curry(api_fn, request))


class _MessageDescriptor(object):
    """
    A descriptor that binds the _MessageAPIWrapper to the view's request.
    """
    def __get__(self, instance, owner):
        return _MessageAPIWrapper(instance.request)


class MessageMixin(object):
    """
    Add a `messages` attribute on the view instance that wraps
    `django.contrib .messages`, automatically passing the current request object.
    """
    messages = _MessageDescriptor()


class SuccessMessageMixin(MessageMixin):
    """
    Adds a success message on successful form submission.
    """
    success_message = ''

    def form_valid(self, form):
        response = super(SuccessMessageMixin, self).form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            self.messages.success(success_message)
        return response

    def get_success_message(self, cleaned_data):
        return self.success_message % cleaned_data
