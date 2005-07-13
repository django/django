"Global CMS exceptions"

from django.core.template import SilentVariableFailure

class Http404(Exception):
    pass

class ObjectDoesNotExist(SilentVariableFailure):
    "The requested object does not exist"
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