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
    pass
