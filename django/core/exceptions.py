"Global Django exceptions"

class ObjectDoesNotExist(Exception):
    "The requested object does not exist"
    silent_variable_failure = True

class MultipleObjectsReturned(Exception):
    "The query returned multiple objects when only one was expected."
    pass

class SuspiciousOperation(Exception):
    "The user did something suspicious"
    pass

class PermissionDenied(Exception):
    "The user did not have permission to do that"
    pass

class ViewDoesNotExist(Exception):
    "The requested view does not exist"
    pass

class MiddlewareNotUsed(Exception):
    "This middleware is not used in this server configuration"
    pass

class ImproperlyConfigured(Exception):
    "Django is somehow improperly configured"
    pass

class FieldError(Exception):
    """Some kind of problem with a model field."""
    pass

class ValidationError(Exception):
    """An error while validating data."""
    def __init__(self, message):
        from django.utils.encoding import force_unicode
        """
        ValidationError can be passed any object that can be printed (usually
        a string) or a list of objects.
        """
        if isinstance(message, list):
            self.messages = [force_unicode(msg) for msg in message]
        else:
            message = force_unicode(message)
            self.messages = [message]

    def __str__(self):
        # This is needed because, without a __str__(), printing an exception
        # instance would result in this:
        # AttributeError: ValidationError instance has no attribute 'args'
        # See http://www.python.org/doc/current/tut/node10.html#handling
        return repr(self.messages)
