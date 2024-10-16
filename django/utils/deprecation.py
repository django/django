import inspect
import os
import warnings

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

import django
from django.utils.version import PY312


class RemovedInDjango60Warning(DeprecationWarning):
    pass


class RemovedInDjango61Warning(PendingDeprecationWarning):
    pass


RemovedInNextVersionWarning = RemovedInDjango60Warning
RemovedAfterNextVersionWarning = RemovedInDjango61Warning


class warn_about_renamed_method:
    def __init__(
        self, class_name, old_method_name, new_method_name, deprecation_warning
    ):
        self.class_name = class_name
        self.old_method_name = old_method_name
        self.new_method_name = new_method_name
        self.deprecation_warning = deprecation_warning

    def __call__(self, f):
        def wrapper(*args, **kwargs):
            warnings.warn(
                "`%s.%s` is deprecated, use `%s` instead."
                % (self.class_name, self.old_method_name, self.new_method_name),
                self.deprecation_warning,
                2,
            )
            return f(*args, **kwargs)

        return wrapper


class RenameMethodsBase(type):
    """
    Handles the deprecation paths when renaming a method.

    It does the following:
        1) Define the new method if missing and complain about it.
        2) Define the old method if missing.
        3) Complain whenever an old method is called.

    See #15363 for more details.
    """

    renamed_methods = ()

    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)

        for base in inspect.getmro(new_class):
            class_name = base.__name__
            for renamed_method in cls.renamed_methods:
                old_method_name = renamed_method[0]
                old_method = base.__dict__.get(old_method_name)
                new_method_name = renamed_method[1]
                new_method = base.__dict__.get(new_method_name)
                deprecation_warning = renamed_method[2]
                wrapper = warn_about_renamed_method(class_name, *renamed_method)

                # Define the new method if missing and complain about it
                if not new_method and old_method:
                    warnings.warn(
                        "`%s.%s` method should be renamed `%s`."
                        % (class_name, old_method_name, new_method_name),
                        deprecation_warning,
                        2,
                    )
                    setattr(base, new_method_name, old_method)
                    setattr(base, old_method_name, wrapper(old_method))

                # Define the old method as a wrapped call to the new method.
                if not old_method and new_method:
                    setattr(base, old_method_name, wrapper(new_method))

        return new_class


class MiddlewareMixin:
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        if get_response is None:
            raise ValueError("get_response must be provided.")
        self.get_response = get_response
        # If get_response is a coroutine function, turns us into async mode so
        # a thread is not consumed during a whole request.
        self.async_mode = iscoroutinefunction(self.get_response)
        if self.async_mode:
            # Mark the class as async-capable, but do the actual switch inside
            # __call__ to avoid swapping out dunder methods.
            markcoroutinefunction(self)
        super().__init__()

    def __repr__(self):
        return "<%s get_response=%s>" % (
            self.__class__.__qualname__,
            getattr(
                self.get_response,
                "__qualname__",
                self.get_response.__class__.__name__,
            ),
        )

    def __call__(self, request):
        # Exit out to async mode, if needed
        if self.async_mode:
            return self.__acall__(request)
        response = None
        if hasattr(self, "process_request"):
            response = self.process_request(request)
        response = response or self.get_response(request)
        if hasattr(self, "process_response"):
            response = self.process_response(request, response)
        return response

    async def __acall__(self, request):
        """
        Async version of __call__ that is swapped in when an async request
        is running.
        """
        response = None
        if hasattr(self, "process_request"):
            response = await sync_to_async(
                self.process_request,
                thread_sensitive=True,
            )(request)
        response = response or await self.get_response(request)
        if hasattr(self, "process_response"):
            response = await sync_to_async(
                self.process_response,
                thread_sensitive=True,
            )(request, response)
        return response


def adjust_stacklevel_for_warning(skip_file_prefixes):
    def _get_non_django_stacklevel():
        django_path = os.path.dirname(django.__file__)
        stacklevel = 1
        # Exclude current and nested function frames with [2:].
        for frame_info in inspect.stack()[2:]:
            filename = os.path.abspath(frame_info.filename)
            if not filename.startswith(django_path):
                return stacklevel
            stacklevel += 1
        return 1

    if PY312:
        return {
            "skip_file_prefixes": (
                os.path.normpath(os.path.dirname(skip_file_prefixes)),
            )
        }
    else:
        return {"stacklevel": _get_non_django_stacklevel()}
