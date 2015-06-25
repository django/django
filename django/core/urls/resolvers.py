from __future__ import unicode_literals

from functools import update_wrapper
import types

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.decorators import available_attrs
from django.utils.functional import cached_property
from django.utils.module_loading import import_module

from .exceptions import NoReverseMatch, Resolver404


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
        if not self.decorators:
            return self.func
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
            args = submatch.args
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
        # We will be appending constraints and decorators to other constraints
        # and decorators, so normalize them to a list now.
        self.constraints = list(constraints or [])
        self.decorators = list(decorators or [])
        self.default_kwargs = default_kwargs or {}

    def __getitem__(self, item):
        raise KeyError(item)

    def get_namespaces(self, name):
        return []

    def match(self, path, request):
        args, kwargs = (), {}
        for constraint in self.constraints:
            path, new_args, new_kwargs = constraint.match(path, request)
            args += new_args
            kwargs.update(new_kwargs)
        kwargs.update(self.default_kwargs)
        return path, args, kwargs


class Resolver(BaseResolver):
    def __init__(self, urlconf_name, app_name=None, constraints=None, decorators=None, default_kwargs=None):
        super(Resolver, self).__init__(constraints, decorators, default_kwargs)
        self.urlconf_name = urlconf_name
        self.app_name = app_name

    def __repr__(self):
        if isinstance(self.urlconf_name, list) and len(self.urlconf_name):
            urlconf_repr = '<%s list>' % self.urlconf_name[0][1].__class__.__name__
        else:
            urlconf_repr = repr(self.urlconf_name)
        return '<%s %s (%s)>' % (self.__class__.__name__, urlconf_repr, self.app_name)

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

    @cached_property
    def _callback_strs(self):
        # Remove this as soon as you can. It's ugly. I hate it.
        # #2.0WillSetUsFree
        callbacks = set()
        processed = [self.urlconf_name]
        queue = [resolver for name, resolver in self.resolvers]
        while queue:
            resolver = queue.pop()
            # If neither of these conditions are true, it's a custom resolver
            # that doesn't resemble any of the built-in ones, and we don't
            # know what to do with it.
            if hasattr(resolver, '_func_str'):
                callbacks.add(resolver._func_str)
            elif hasattr(resolver, 'urlconf_name'):
                processed.append(resolver.urlconf_name)
                queue.extend(
                    resolver for name, resolver in resolver.resolvers
                    if not hasattr(resolver, 'urlconf_name') or resolver.urlconf_name not in processed
                )
        return callbacks

    def _is_callback(self, name):
        return name in self._callback_strs

    def resolve_error_handler(self, view_type):
        callback = getattr(self.urlconf_module, 'handler%s' % view_type, None)
        if not callback:
            # No handler specified in file; use default
            # Lazy import, since django.urls imports this file
            from django.conf import urls
            callback = getattr(urls, 'handler%s' % view_type)
        from django.core.urlresolvers import get_callable
        return get_callable(callback), {}

    def resolve(self, path, request=None):
        new_path, args, kwargs = self.match(path, request)

        tried = []
        for name, resolver in self.resolvers:
            try:
                sub_match = resolver.resolve(new_path, request)
            except Resolver404 as e:
                if e.tried:
                    tried.extend([(name, resolver)] + t for t in e.tried)
                else:
                    tried.append([(name, resolver)])
                continue
            return ResolverMatch.from_submatch(
                sub_match, args, kwargs, self.app_name,
                name, self.decorators
            )
        raise Resolver404(path=new_path, tried=tried)

    def __getitem__(self, item):
        for name, resolver in self.resolvers:
            if name and name == item:
                return resolver
            elif name is None:
                try:
                    return resolver[item]
                except KeyError:
                    pass
        raise KeyError(item)

    def get_namespaces(self, name):
        namespaces = []
        for namespace, resolver in self.resolvers:
            if name and (name == resolver.app_name or namespace == name):
                namespaces.append(namespace)
            elif namespace is None:
                namespaces.extend(resolver.get_namespaces(name))
        return namespaces

    def resolve_namespace(self, lookup, current_app):
        if not lookup:
            raise NoReverseMatch()
        namespaces = self.get_namespaces(lookup[0])
        if current_app and current_app[0] in namespaces:
            name = current_app[0]
        elif lookup[0] in namespaces:
            name = lookup[0]
            current_app = []
        elif namespaces:
            name = namespaces[-1]
            current_app = []
        else:
            return lookup

        return [name] + self[name].resolve_namespace(lookup[1:], current_app[1:])

    def search(self, lookup):
        if not lookup:
            return
        lookup_name, lookup_path = lookup[0], lookup[1:]

        # For historical reasons we search through the patterns backwards.
        for name, resolver in reversed(self.resolvers):
            if name and name == lookup_name:
                for constraints, default_kwargs in resolver.search(lookup_path):
                    default_kwargs.update(self.default_kwargs)
                    yield self.constraints + constraints, default_kwargs
            elif not name:
                for constraints, default_kwargs in resolver.search(lookup):
                    default_kwargs.update(self.default_kwargs)
                    yield self.constraints + constraints, default_kwargs


class ResolverEndpoint(BaseResolver):
    def __init__(self, func, url_name=None, constraints=None, decorators=None, default_kwargs=None):
        super(ResolverEndpoint, self).__init__(constraints, decorators, default_kwargs)
        if callable(func):
            self._func = func
            if not hasattr(func, '__name__'):
                # A class-based view
                self._func_str = '.'.join([func.__class__.__module__, func.__class__.__name__])
            else:
                # A function-based view
                self._func_str = '.'.join([func.__module__, func.__name__])
        else:
            self._func = None
            self._func_str = func
        self.url_name = url_name

    def __repr__(self):
        return "<%s %s (%s)>" % (self.__class__.__name__, self.url_name, self._func_str)

    def add_prefix(self, prefix):
        if callable(self._func) or not prefix:
            return
        self._func_str = prefix + '.' + self._func_str

    @property
    def func(self):
        if self._func is None:
            from django.core.urlresolvers import get_callable
            self._func = get_callable(self._func_str)
        return self._func

    @cached_property
    def _callback_strs(self):
        return {self._func_str}

    def resolve(self, path, request=None):
        new_path, args, kwargs = self.match(path, request)
        return ResolverMatch(self.func, args, kwargs, self.url_name, decorators=self.decorators)

    def __getitem__(self, item):
        if item and item in (self.url_name, self._func_str):
            return self
        raise KeyError(item)

    def resolve_namespace(self, lookup, current_app):
        if len(lookup) == 1 and lookup[0] and lookup[0] in (self.url_name, self._func):
            return lookup
        raise NoReverseMatch()

    def search(self, lookup):
        if len(lookup) == 1 and lookup[0] and lookup[0] in (self.url_name, self._func):
            yield self.constraints, self.default_kwargs.copy()
        return
