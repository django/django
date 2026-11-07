from django.core.exceptions import ImproperlyConfigured


class TaskException(Exception):
    """Base class for task-related exceptions. Do not raise directly."""


class InvalidTask(ValueError, TaskException):
    """The provided Task is invalid."""


class InvalidTaskBackend(ImproperlyConfigured):
    """The provided Task backend is invalid."""


class TaskDoesNotExist(ValueError, TaskException):
    """The requested TaskResult does not exist."""

    def __init__(self, func_path, *args: object):
        super().__init__(f"Expected {func_path!r} to point to a Task instance.")


class TaskResultDoesNotExist(TaskException):
    """The requested TaskResult does not exist."""


class TaskResultMismatch(TaskException):
    """The requested TaskResult is invalid."""
