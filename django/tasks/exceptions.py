from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist


class InvalidTaskError(Exception):
    """
    The provided Task is invalid.
    """


class InvalidTaskBackendError(ImproperlyConfigured):
    pass


class ResultDoesNotExist(ObjectDoesNotExist):
    pass


class TaskIntegrityError(ObjectDoesNotExist):
    pass
