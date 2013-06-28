"""
Global Django exception and warning classes.
"""
from functools import reduce
import operator

from django.utils.encoding import force_text


class DjangoRuntimeWarning(RuntimeWarning):
    pass


class ObjectDoesNotExist(Exception):
    """The requested object does not exist"""
    silent_variable_failure = True


class MultipleObjectsReturned(Exception):
    """The query returned multiple objects when only one was expected."""
    pass


class SuspiciousOperation(Exception):
    """The user did something suspicious"""


class SuspiciousMultipartForm(SuspiciousOperation):
    """Suspect MIME request in multipart form data"""
    pass


class SuspiciousFileOperation(SuspiciousOperation):
    """A Suspicious filesystem operation was attempted"""
    pass


class DisallowedHost(SuspiciousOperation):
    """HTTP_HOST header contains invalid value"""
    pass


class DisallowedRedirect(SuspiciousOperation):
    """Redirect to scheme not in allowed list"""
    pass


class PermissionDenied(Exception):
    """The user did not have permission to do that"""
    pass


class ViewDoesNotExist(Exception):
    """The requested view does not exist"""
    pass


class MiddlewareNotUsed(Exception):
    """This middleware is not used in this server configuration"""
    pass


class ImproperlyConfigured(Exception):
    """Django is somehow improperly configured"""
    pass


class FieldError(Exception):
    """Some kind of problem with a model field."""
    pass


NON_FIELD_ERRORS = '__all__'


class ValidationError(Exception):
    """An error while validating data."""
    def __init__(self, message, code=None, params=None):
        """
        ValidationError can be passed any object that can be printed (usually
        a string), a list of objects or a dictionary.
        """
        if isinstance(message, dict):
            self.error_dict = message
        elif isinstance(message, list):
            self.error_list = message
        else:
            self.code = code
            self.params = params
            self.message = message
            self.error_list = [self]

    @property
    def message_dict(self):
        message_dict = {}
        for field, messages in self.error_dict.items():
            message_dict[field] = []
            for message in messages:
                if isinstance(message, ValidationError):
                    message_dict[field].extend(message.messages)
                else:
                    message_dict[field].append(force_text(message))
        return message_dict

    @property
    def messages(self):
        if hasattr(self, 'error_dict'):
            message_list = reduce(operator.add, self.error_dict.values())
        else:
            message_list = self.error_list

        messages = []
        for message in message_list:
            if isinstance(message, ValidationError):
                params = message.params
                message = message.message
                if params:
                    message %= params
            message = force_text(message)
            messages.append(message)
        return messages

    def __str__(self):
        if hasattr(self, 'error_dict'):
            return repr(self.message_dict)
        return repr(self.messages)

    def __repr__(self):
        return 'ValidationError(%s)' % self

    def update_error_dict(self, error_dict):
        if hasattr(self, 'error_dict'):
            if error_dict:
                for k, v in self.error_dict.items():
                    error_dict.setdefault(k, []).extend(v)
            else:
                error_dict = self.error_dict
        else:
            error_dict[NON_FIELD_ERRORS] = self.error_list
        return error_dict
