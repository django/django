from __future__ import unicode_literals

from functools import update_wrapper

from django.utils.decorators import available_attrs
from django.utils.functional import cached_property


class ResolverMatch(object):
    def __init__(self, func, args, kwargs, url_name=None, app_names=None, namespaces=None, decorators=None):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.url_name = url_name
        self.app_names = [x for x in app_names if x] if app_names else []
        self.namespaces = [x for x in namespaces if x] if namespaces else []
        self.decorators = decorators or []

        if not hasattr(func, '__name__'):
            self._func_path = '.'.join([func.__class__.__module__, func.__class__.__name__])
        else:
            self._func_path = '.'.join([func.__module__, func.__name__])

    @cached_property
    def app_name(self):
        """
        Return the fully qualified application namespace.
        """
        return ':'.join(self.app_names)

    @cached_property
    def namespace(self):
        """
        Return the fully qualified instance namespace.
        """
        return ':'.join(self.namespaces)

    @cached_property
    def view_name(self):
        """
        Return the fully qualified view name, consisting of the instance
        namespace and the view's name.
        """
        view_name = self.url_name or self._func_path
        return ':'.join(self.namespaces + [view_name])

    @cached_property
    def callback(self):
        """
        Return the decorated callback function.
        """
        callback = func = self.func
        for decorator in reversed(self.decorators):
            callback = decorator(callback)
        update_wrapper(callback, func, assigned=available_attrs(func))
        return callback

    def __getitem__(self, index):
        return (self.callback, self.args, self.kwargs)[index]

    def __repr__(self):
        return "ResolverMatch(func=%s, args=%s, kwargs=%s, url_name=%s, app_names=%s, namespaces=%s)" % (
            self._func_path, self.args, self.kwargs, self.url_name, self.app_names, self.namespaces)

    @classmethod
    def from_submatch(cls, submatch, args, kwargs, app_name=None, namespace=None, decorators=None):
        """
        Create a new ResolverMatch, carrying over any properties from
        submatch. Does not carry over args if there are any kwargs.
        """
        if kwargs or submatch.kwargs:
            args = ()
            kwargs.update(submatch.kwargs)
        else:
            args += submatch.args
        app_names = ([app_name] if app_name else []) + submatch.app_names
        namespaces = ([namespace] if namespace else []) + submatch.namespaces
        decorators = (decorators or []) + submatch.decorators
        return cls(submatch.func, args, kwargs, submatch.url_name, app_names, namespaces, decorators)
