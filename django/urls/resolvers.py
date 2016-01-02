"""
This module converts requested URLs to callback view functions.

RegexURLResolver is the main class here. Its resolve() method takes a URL (as
a string) and returns a ResolverMatch object which provides access to all
attributes of the resolved URL match.
"""
from __future__ import unicode_literals

from functools import partial, update_wrapper

from django.conf.urls import Include, URLConf, URLPattern
from django.utils import lru_cache
from django.utils.decorators import available_attrs
from django.utils.functional import cached_property

from .constraints import RegexPattern, ScriptPrefix
from .exceptions import Resolver404


class ResolverMatch(object):
    def __init__(self, endpoint, args, kwargs, app_names=None, namespaces=None):
        self.endpoint = endpoint
        self.args = args
        self.kwargs = kwargs
        self.app_names = [x for x in app_names if x] if app_names else []
        self.namespaces = [x for x in namespaces if x] if namespaces else []

    @cached_property
    def func(self):
        return self.endpoint.func

    @cached_property
    def callback(self):
        return getattr(self.endpoint, 'callback', self.func)

    @cached_property
    def url_name(self):
        return getattr(self.endpoint, 'url_name', None)

    @cached_property
    def _func_path(self):
        if hasattr(self.endpoint, 'lookup_str'):
            return self.endpoint.lookup_str

        func = self.func
        if isinstance(func, partial):
            func = func.func
        if not hasattr(func, '__name__'):
            return func.__module__ + "." + func.__class__.__name__
        else:
            return func.__module__ + "." + func.__name__

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

    def __getitem__(self, index):
        return (self.callback, self.args, self.kwargs)[index]

    def __repr__(self):
        return "ResolverMatch(func=%s, args=%s, kwargs=%s, url_name=%s, app_names=%s, namespaces=%s)" % (
            self._func_path, self.args, self.kwargs, self.url_name,
            self.app_names, self.namespaces,
        )

    @classmethod
    def from_submatch(cls, submatch, args, kwargs, app_name=None, namespace=None):
        """
        Create a new ResolverMatch, carrying over any properties from
        submatch. Does not carry over args if there are any kwargs.
        """
        if kwargs or submatch.kwargs:
            args = submatch.args
            kwargs.update(submatch.kwargs)
        else:
            args += submatch.args
        app_names = ([app_name] if app_name else []) + submatch.app_names
        namespaces = ([namespace] if namespace else []) + submatch.namespaces
        return cls(submatch.endpoint, args, kwargs, app_names, namespaces)


@lru_cache.lru_cache(maxsize=None)
def get_resolver(urlconf=None):
    if urlconf is None:
        from django.conf import settings
        urlconf = settings.ROOT_URLCONF
    return Resolver(URLPattern([ScriptPrefix()], Include(URLConf(urlconf))))


class BaseResolver(object):
    def __init__(self, pattern, decorators=None):
        self.constraints = list(pattern.constraints)
        self.kwargs = pattern.target.kwargs.copy()
        self.decorators = list(decorators or [])
        self.decorators.extend(pattern.target.decorators)

    def is_endpoint(self):
        raise NotImplementedError("Subclasses of 'BaseResolver' must implement the 'is_endpoint' method.")

    def resolve(self, path, request):
        raise NotImplementedError("Subclasses of 'BaseResolver' must implement the 'resolve' method.")

    def match(self, path, request):
        args, kwargs = (), {}
        for constraint in self.constraints:
            path, new_args, new_kwargs = constraint.match(path, request)
            args += new_args
            kwargs.update(new_kwargs)
        kwargs.update(self.kwargs)
        return path, args, kwargs

    def describe(self):
        description = ''.join(constraint.describe() for constraint in self.constraints)
        if isinstance(self.constraints[0], RegexPattern) and self.constraints[0].regex.pattern.startswith('^'):
            description = '^%s' % description
        return description


class Resolver(BaseResolver):
    def __init__(self, pattern, *args, **kwargs):
        super(Resolver, self).__init__(pattern, *args, **kwargs)
        self.urlconf = pattern.target.urlconf
        self.namespace = pattern.target.namespace
        self.app_name = pattern.target.urlconf.app_name

    def is_endpoint(self):
        return False

    def __repr__(self):
        if isinstance(self.urlconf.urlpatterns, list) and len(self.urlconf.urlpatterns):
            urlconf_repr = '<%s list>' % self.resolvers[0].__class__.__name__
        else:
            urlconf_repr = repr(self.urlconf.urlconf_name)
        return '<%s %s (%s)>' % (self.__class__.__name__, urlconf_repr, self.app_name)

    @cached_property
    def resolvers(self):
        return [
            ResolverEndpoint(pattern, decorators=self.decorators) if pattern.is_view()
            else Resolver(pattern, decorators=self.decorators)
            for pattern in self.urlconf.urlpatterns
        ]

    def resolve(self, path, request=None):
        new_path, args, kwargs = self.match(path, request)

        tried = []
        for resolver in self.resolvers:
            try:
                sub_match = resolver.resolve(new_path, request)
            except Resolver404 as e:
                if e.tried:
                    tried.extend([resolver] + t for t in e.tried)
                else:
                    tried.append([resolver])
                continue
            return ResolverMatch.from_submatch(sub_match, args, kwargs, self.app_name, self.namespace)
        raise Resolver404(path=new_path, tried=tried)

    @cached_property
    def urlconf_module(self):
        return self.urlconf.urlconf_module


class ResolverEndpoint(BaseResolver):
    def __init__(self, pattern, *args, **kwargs):
        super(ResolverEndpoint, self).__init__(pattern, *args, **kwargs)
        self.func = pattern.target.view
        self.lookup_str = pattern.target.lookup_str
        self.url_name = pattern.target.url_name

    def is_endpoint(self):
        return True

    def __repr__(self):
        return "<%s %s (%s)>" % (self.__class__.__name__, self.url_name, self.lookup_str)

    @cached_property
    def callback(self):
        if not self.decorators:
            return self.func
        callback = self.func
        for decorator in reversed(self.decorators):
            callback = decorator(callback)
        update_wrapper(callback, self.func, assigned=available_attrs(self.func))
        return callback

    def resolve(self, path, request=None):
        new_path, args, kwargs = self.match(path, request)
        return ResolverMatch(self, args, kwargs)
