from django.core import checks


class BaseDatabaseValidation(object):
    """
    This class encapsulates all backend-specific model validation.
    """
    def __init__(self, connection):
        self.connection = connection

    def validate_field(self, errors, opts, f):
        """
        By default, there is no backend-specific validation.

        This method has been deprecated by the new checks framework. New
        backends should implement check_field instead.
        """
        # This is deliberately commented out. It exists as a marker to
        # remind us to remove this method, and the check_field() shim,
        # when the time comes.
        # warnings.warn('"validate_field" has been deprecated", RemovedInDjango19Warning)
        pass

    def check_field(self, field, **kwargs):
        class ErrorList(list):
            """A dummy list class that emulates API used by the older
            validate_field() method. When validate_field() is fully
            deprecated, this dummy can be removed too.
            """
            def add(self, opts, error_message):
                self.append(checks.Error(error_message, hint=None, obj=field))

        errors = ErrorList()
        # Some tests create fields in isolation -- the fields are not attached
        # to any model, so they have no `model` attribute.
        opts = field.model._meta if hasattr(field, 'model') else None
        self.validate_field(errors, field, opts)
        return list(errors)
