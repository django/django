from __future__ import unicode_literals

from functools import update_wrapper

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.datastructures import MultiValueDict
from django.utils.decorators import available_attrs
from django.utils.functional import cached_property
from django.utils.module_loading import import_module

from .exceptions import Resolver404


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


class BaseResolver(object):
    app_name = None

    def __init__(self, constraints=None, decorators=None, default_kwargs=None):
        self.constraints = constraints or []
        self.decorators = decorators or []
        self.default_kwargs = default_kwargs or {}

    def match(self, url, request):
        args, kwargs = (), {}
        for constraint in self.constraints:
            url, new_args, new_kwargs = constraint.match(url, request)
            args += new_args
            kwargs.update(new_kwargs)
        kwargs.update(self.default_kwargs)
        return url, args, kwargs


class Resolver(BaseResolver):
    def __init__(self, urlconf_name, app_name=None, constraints=None, decorators=None, default_kwargs=None):
        super(Resolver, self).__init__(constraints, decorators, default_kwargs)
        self.urlconf_name = urlconf_name
        self.app_name = app_name

    @cached_property
    def urlconf_module(self):
        if isinstance(self.urlconf_name, six.string_types):
            return import_module(self.urlconf_name)
        else:
            return self.urlconf_name

    @cached_property
    def resolvers(self):
        # urlconf_module might be a valid set of patterns, so we default to it
        patterns = getattr(self.urlconf_module, "urlpatterns", self.urlconf_module)
        try:
            iter(patterns)
        except TypeError:
            msg = (
                "The included urlconf '{name}' does not appear to have any "
                "patterns in it. If you see valid patterns in the file then "
                "the issue is probably caused by a circular import."
            )
            raise ImproperlyConfigured(msg.format(name=self.urlconf_name))
        return patterns

    def resolve(self, url, request=None):
        new_url, args, kwargs = self.match(url, request)
        for name, resolver in self.resolvers:
            try:
                sub_match = resolver.resolve(new_url, request)
            except Resolver404:
                continue
            return ResolverMatch.from_submatch(
                sub_match, args, kwargs, self.app_name,
                name, self.decorators
            )
        raise Resolver404()

    @cached_property
    def app_dict(self):
        dict_ = MultiValueDict()
        for name, resolver in self.resolvers:
            if name and resolver.app_name:
                dict_.appendlist(resolver.app_name, name)
        return dict_

    def resolve_namespace(self, name, current_app):
        if not name:
            if current_app:
                return current_app[0]
            return name
        if current_app:
            if name in self.app_dict and current_app[0] in self.app_dict.getlist(name):
                return current_app[0]
        if name in self.app_dict and name not in self.app_dict.getlist(name):
            return self.app_dict[name]
        return name

    def search(self, lookup, current_app):
        if not lookup:
            return
        lookup_name = self.resolve_namespace(lookup[0], current_app)
        lookup_path = lookup[1:]
        current_app_path = current_app[1:]

        for name, resolver in reversed(self.resolvers):
            if name and name == lookup_name:
                for constraints, default_kwargs in resolver.search(lookup_path, current_app_path):
                    default_kwargs.update(self.default_kwargs)
                    yield self.constraints + constraints, default_kwargs
            elif not name:
                for constraints, default_kwargs in resolver.search(lookup, current_app):
                    default_kwargs.update(self.default_kwargs)
                    yield self.constraints + constraints, default_kwargs


class ResolverEndpoint(BaseResolver):
    def __init__(self, func, url_name=None, constraints=None, decorators=None, default_kwargs=None):
        super(ResolverEndpoint, self).__init__(constraints, decorators, default_kwargs)
        self._func = func
        if not hasattr(func, '__name__'):
            # A class-based view
            self._func_path = '.'.join([func.__class__.__module__, func.__class__.__name__])
        else:
            # A function-based view
            self._func_path = '.'.join([func.__module__, func.__name__])
        self.url_name = url_name

    def __repr__(self):
        return "<ResolverEndpoint func=%s name=%s>" % (self._func_path, self.url_name)

    def add_prefix(self, prefix):
        if callable(self._func) or not prefix:
            return
        self._func = prefix + '.' + self._func

    @property
    def func(self):
        if not callable(self._func):
            from django.core.urlresolvers import get_callable
            self._func = get_callable(self._func)
        return self._func

    def resolve(self, url, request=None):
        new_url, args, kwargs = self.match(url, request)
        return ResolverMatch(self.func, args, kwargs, self.url_name, decorators=self.decorators)

    def search(self, lookup, current_app):
        if len(lookup) == 1 and (self.url_name and lookup[0] == self.url_name or lookup[0] == self._func_path or lookup[0] is self.func):
            yield self.constraints, self.default_kwargs.copy()
        return
