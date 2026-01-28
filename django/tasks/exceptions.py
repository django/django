from django.core.exceptions import ImproperlyConfigured


class TaskException(Exception):
    """Base class for task-related exceptions. Do not raise directly."""


class InvalidTask(TaskException):
    """The provided Task is invalid."""


class InvalidTaskBackend(ImproperlyConfigured):
    """The provided Task backend is invalid."""


class TaskResultDoesNotExist(TaskException):
    """The requested TaskResult does not exist."""


class TaskResultMismatch(TaskException):
    """The requested TaskResult is invalid."""
