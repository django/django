from __future__ import absolute_import

import inspect
import warnings


class RemovedInDjango20Warning(PendingDeprecationWarning):
    pass


class RemovedInNextVersionWarning(DeprecationWarning):
    pass


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


class DeprecationInstanceCheck(type):
    def __instancecheck__(self, instance):
        warnings.warn(
            "`%s` is deprecated, use `%s` instead." % (self.__name__, self.alternative),
            self.deprecation_warning, 2
        )
        return super(DeprecationInstanceCheck, self).__instancecheck__(instance)


class CallableBool:
    """
    An boolean-like object that is also callable for backwards compatibility.
    """
    do_not_call_in_templates = True

    def __init__(self, value):
        self.value = value

    def __bool__(self):
        return self.value

    def __call__(self):
        warnings.warn(
            "Using user.is_authenticated() and user.is_anonymous() as a method "
            "is deprecated. Remove the parentheses to use it as an attribute.",
            RemovedInDjango20Warning, stacklevel=2
        )
        return self.value

    def __nonzero__(self):  # Python 2 compatibility
        return self.value

    def __repr__(self):
        return 'CallableBool(%r)' % self.value

CallableFalse = CallableBool(False)
CallableTrue = CallableBool(True)


class MiddlewareMixin(object):
    def __init__(self, get_response=None):
        self.get_response = get_response
        super(MiddlewareMixin, self).__init__()

    def __call__(self, request):
        response = None
        if hasattr(self, 'process_request'):
            response = self.process_request(request)
        if not response:
            try:
                response = self.get_response(request)
            except Exception as e:
                if hasattr(self, 'process_exception'):
                    return self.process_exception(request, e)
                else:
                    raise
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        return response
