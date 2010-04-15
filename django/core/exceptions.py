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

NON_FIELD_ERRORS = '__all__'
class ValidationError(Exception):
    """An error while validating data."""
    def __init__(self, message, code=None, params=None):
        import operator
        from django.utils.encoding import force_unicode
        """
        ValidationError can be passed any object that can be printed (usually
        a string), a list of objects or a dictionary.
        """
        if isinstance(message, dict):
            self.message_dict = message
            # Reduce each list of messages into a single list.
            message = reduce(operator.add, message.values())

        if isinstance(message, list):
            self.messages = [force_unicode(msg) for msg in message]
        else:
            self.code = code
            self.params = params
            message = force_unicode(message)
            self.messages = [message]

    def __str__(self):
        # This is needed because, without a __str__(), printing an exception
        # instance would result in this:
        # AttributeError: ValidationError instance has no attribute 'args'
        # See http://www.python.org/doc/current/tut/node10.html#handling
        if hasattr(self, 'message_dict'):
            return repr(self.message_dict)
        return repr(self.messages)

    def __repr__(self):
        if hasattr(self, 'message_dict'):
            return 'ValidationError(%s)' % repr(self.message_dict)
        return 'ValidationError(%s)' % repr(self.messages)

    def update_error_dict(self, error_dict):
        if hasattr(self, 'message_dict'):
            if error_dict:
                for k, v in self.message_dict.items():
                    error_dict.setdefault(k, []).extend(v)
            else:
                error_dict = self.message_dict
        else:
            error_dict[NON_FIELD_ERRORS] = self.messages
        return error_dict

