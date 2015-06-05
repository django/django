import functools
import inspect
import warnings


class RemovedInDjango21Warning(PendingDeprecationWarning):
    pass


class RemovedInDjango20Warning(DeprecationWarning):
    pass


RemovedInNextVersionWarning = RemovedInDjango20Warning


class warn_about_renamed_method(object):
    def __init__(self, class_name, old_method_name, new_method_name, deprecation_warning):
        self.class_name = class_name
        self.old_method_name = old_method_name
        self.new_method_name = new_method_name
        self.deprecation_warning = deprecation_warning

    def __call__(self, f):
        def wrapped(*args, **kwargs):
            warnings.warn(
                "`%s.%s` is deprecated, use `%s` instead." %
                (self.class_name, self.old_method_name, self.new_method_name),
                self.deprecation_warning, 2)
            return f(*args, **kwargs)
        return wrapped


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
        new_class = super(RenameMethodsBase, cls).__new__(cls, name, bases, attrs)

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
                        "`%s.%s` method should be renamed `%s`." %
                        (class_name, old_method_name, new_method_name),
                        deprecation_warning, 2)
                    setattr(base, new_method_name, old_method)
                    setattr(base, old_method_name, wrapper(old_method))

                # Define the old method as a wrapped call to the new method.
                if not old_method and new_method:
                    setattr(base, old_method_name, wrapper(new_method))

        return new_class


def deprecate_current_app(func):
    """
    Handles deprecation of the current_app argument of auth views
    See #24126
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        if "current_app" in kwargs:
            warnings.warn(
                "Passing `current_app` as a keyword argument is deprecated "
                "since Django 1.8, as the caller of `{0}` is required to set "
                "it on the `request`".format(func.func_name),
                RemovedInDjango20Warning
            )
            current_app = kwargs.pop("current_app")
            request = kwargs.get("request", None)
            if request and current_app is not None:
                request.current_app = current_app
        return func(*args, **kwargs)
    return inner
