import functools
import inspect
import warnings
from collections import Counter

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async


class RemovedInDjango61Warning(DeprecationWarning):
    pass


class RemovedInDjango70Warning(PendingDeprecationWarning):
    pass


RemovedInNextVersionWarning = RemovedInDjango61Warning
RemovedAfterNextVersionWarning = RemovedInDjango70Warning


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


def deprecate_posargs(category, *, moved):
    """
    Function/method decorator to deprecate some or all positional arguments.
    The decorated function will map any positional arguments after the `*`
    to the corresponding keyword arguments, but issue a deprecation warning.

    Works on both functions and methods. To apply to a class constructor,
    decorate its __init__() method.

    Example: to deprecate passing option1 or option2 as posargs, change::
        def some_func(request, option1, option2=True):
            ...

    to::
        @deprecate_posargs(RemovedInDjangoNMWarning, moved=["option1", "option2"])
        def some_func(request, *, option1, option2=True):
            ...

    `moved` must be a list of the formerly positional-or-keyword parameters
    that are now keyword-only, in their original positional order.

    After the deprecation period, remove the decorator (but keep the `*`).

    Caution: during the deprecation period, you must not add or remove any
    positional parameters. (But it's OK to re-order or add keyword-only params.)
    """

    def decorator(func):
        if isinstance(func, type):
            raise TypeError(
                "@deprecate_posargs cannot be applied to a class."
                " (Apply it to the __init__ method.)"
            )
        if isinstance(func, classmethod):
            raise TypeError("Apply @classmethod before @deprecate_posargs.")
        if isinstance(func, staticmethod):
            raise TypeError("Apply @staticmethod before @deprecate_posargs.")

        params = inspect.signature(func).parameters
        num_by_kind = Counter(param.kind for param in params.values())

        if num_by_kind[inspect.Parameter.VAR_POSITIONAL] > 0:
            raise TypeError(
                "@deprecate_posargs() cannot be used with variable positional `*args`."
            )

        num_positional_params = (
            num_by_kind[inspect.Parameter.POSITIONAL_ONLY]
            + num_by_kind[inspect.Parameter.POSITIONAL_OR_KEYWORD]
        )
        num_keyword_only_params = num_by_kind[inspect.Parameter.KEYWORD_ONLY]
        if num_keyword_only_params < 1:
            raise TypeError(
                "@deprecate_posargs() requires at least one keyword-only parameter"
                " (after a `*` entry in the parameters list)."
            )
        if any(
            name not in params or params[name].kind != inspect.Parameter.KEYWORD_ONLY
            for name in moved
        ):
            raise TypeError(
                "@deprecate_posargs() `moved` names must"
                " all be keyword-only parameters."
            )

        num_moveable_args = len(moved)
        max_positional_args = num_positional_params + num_moveable_args

        param_names = list(params.keys())

        # The deprecation message logic needs to know if func is a bound method.
        # Because decorators always receive plain, unbound functions, the class
        # information is not available here. (inspect.ismethod(func) will always
        # return False, and func.__self__ will never be set.) This only affects
        # message construction, not argument mapping logic, so it's fine to just
        # look for the customary bound parameter names.
        num_bound_params = 1 if param_names[0] in ("self", "cls") else 0
        func_name = func.__name__
        if func_name == "__init__":
            # In the warning, show "ClassName(...)" rather than "__init__(...)".
            # The class isn't defined yet, but its name is in __qualname__.
            # Some examples: "ClassName.__init__", "Nested.ClassName.__init__",
            # "MyTests.test_case.<locals>.ClassName.__init__".
            try:
                local_name = func.__qualname__.rsplit("<locals>.", 1)[-1]
                class_name = local_name.replace(".__init__", "")
            except (AttributeError, IndexError, TypeError):
                # __init__ outside a class or other oddity. The __name__ is fine.
                pass
            else:
                func_name = class_name

        if num_positional_params > num_bound_params:
            # Clarify that only "some" (not all) positional arguments are affected.
            message_template = (
                "Use of some positional arguments is deprecated."
                " Change to `{replacement}`."
            )
        else:
            message_template = (
                "Use of positional arguments is deprecated."
                " Change to `{replacement}`."
            )

        def remap_deprecated_args(args, kwargs):
            """
            Move deprecated positional args to kwargs and issue a warning.
            Returns updated (args, kwargs).
            """
            num_positional_args = len(args)
            if num_positional_args > max_positional_args:
                raise TypeError(
                    f"{func_name}() takes"
                    f" at most {max_positional_args} positional argument(s)"
                    f" (including {num_moveable_args} deprecated)"
                    f" but {num_positional_args} were given."
                )

            moved_names = moved[: num_positional_args - num_positional_params]
            conflicts = set(moved_names) & set(kwargs)
            if conflicts:
                # Report duplicate param names in original parameter order.
                conflicts_str = ", ".join(
                    f"'{name}'" for name in moved_names if name in conflicts
                )
                raise TypeError(
                    f"{func_name}() got both deprecated positional and keyword"
                    f" argument values for {conflicts_str}."
                )

            # Do the remapping.
            moved_kwargs = dict(zip(moved_names, args[num_positional_params:]))
            remaining_args = args[:num_positional_params]
            updated_kwargs = kwargs | moved_kwargs

            # Issue the deprecation warning. Construct a suggested replacement
            # showing the affected arguments:
            #     "Change to `func_name(..., kwonly1=..., kwonly2=..., ...)`."
            # - Initial "..." represents remaining (non-remapped) positional args,
            #   excluding `self` or `cls`.
            # - Trailing "..." represents other (non-remapped) keyword args.
            replacement_args = [f"{name}=..." for name in moved_names]
            if len(remaining_args) > num_bound_params:
                replacement_args.insert(0, "...")
            if kwargs:
                replacement_args.append("...")
            replacement_args_str = ", ".join(replacement_args)
            replacement = f"{func_name}({replacement_args_str})"

            message = message_template.format(replacement=replacement)
            warnings.warn(message, category, stacklevel=3)

            return remaining_args, updated_kwargs

        if iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if len(args) > num_positional_params:
                    args, kwargs = remap_deprecated_args(args, kwargs)
                return await func(*args, **kwargs)

        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if len(args) > num_positional_params:
                    args, kwargs = remap_deprecated_args(args, kwargs)
                return func(*args, **kwargs)

        return wrapper

    return decorator


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
