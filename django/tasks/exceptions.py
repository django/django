from django.core.exceptions import ImproperlyConfigured


class ResultUnavailable(Exception):
    pass


class ResultUnknown(ResultUnavailable):
    pass


class ResultPending(ResultUnavailable):
    pass


class InvalidTaskBackendError(ImproperlyConfigured):
    pass
