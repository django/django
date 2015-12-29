from __future__ import unicode_literals

from collections import OrderedDict, defaultdict
from importlib import import_module

from django.conf import urls
from django.conf.urls import URLConf, URLPattern
from django.template.context import BaseContext
from django.utils import lru_cache, six
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit
from django.utils.translation import override

from .constraints import ScriptPrefix
from .exceptions import NoReverseMatch, Resolver404
from .resolvers import Resolver
from .utils import URL, describe_constraints, get_callable, get_lookup_string


@lru_cache.lru_cache(maxsize=None)
def get_dispatcher(urlconf):
    return Dispatcher(urlconf)


class Dispatcher(object):
    def __init__(self, urlconf):
        self.urlconf_name = urlconf
        root_pattern = URLPattern([ScriptPrefix()], URLConf(urlconf))
        self.resolver = Resolver(root_pattern)
        self.reverser = Namespace(root_pattern, root_pattern.constraints)

    def __repr__(self):
        return "<Dispatcher '%s'>" % self.urlconf_name

    def get_views(self, lookup, current_app=None):
        if isinstance(lookup, six.string_types):
            lookup = lookup.split(':')
        elif lookup:
            lookup = [lookup]
        else:
            raise NoReverseMatch("View name must not be empty; got '%s'" % (lookup,))

        if current_app:
            current_app = current_app.split(':')

        try:
            return self.reverser.get_views(lookup, current_app)
        except KeyError:
            pass
        raise NoReverseMatch(self.reverser.get_error_message(lookup))

    def reverse(self, views, *args, **kwargs):
        for view in views:
            try:
                url = view.reverse(*args, **kwargs)
            except NoReverseMatch:
                pass
            else:
                return six.text_type(url)

        raise NoReverseMatch(
            "Reverse for '%s' with arguments '%s' and keyword "
            "arguments '%s' not found. %d pattern(s) tried: %s" %
            (
                views[0].url_name, args, kwargs, len(views),
                [str(describe_constraints(view.constraints)) for view in views],
            )
        )

    @cached_property
    def urlconf_module(self):
        if isinstance(self.urlconf_name, six.string_types):
            return import_module(self.urlconf_name)
        else:
            return self.urlconf_name

    def resolve(self, path, request=None):
        return next(self.resolver.resolve(path, request))

    def resolve_error_handler(self, view_type):
        callback = getattr(self.urlconf_module, 'handler%s' % view_type, None)
        if not callback:
            # No handler specified in file; use default
            callback = getattr(urls, 'handler%s' % view_type)
        return get_callable(callback), {}

    def is_valid_path(self, path, request=None):
        """
        Returns True if the given path resolves against the default URL resolver,
        False otherwise.

        This is a convenience method to make working with "is this a match?" cases
        easier, avoiding unnecessarily indented try...except blocks.
        """
        try:
            self.resolve(path, request)
            return True
        except Resolver404:
            return False

    def translate_url(self, url, lang_code, request=None):
        """
        Given a URL (absolute or relative), try to get its translated version in
        the `lang_code` language (either by i18n_patterns or by translated regex).
        Return the original URL if no translated version is found.
        """
        parsed = urlsplit(url)
        try:
            match = self.resolve(parsed.path, request=request)
        except Resolver404:
            pass
        else:
            to_be_reversed = "%s:%s" % (match.namespace, match.url_name) if match.namespace else match.url_name
            with override(lang_code):
                try:
                    views = self.get_views(to_be_reversed)
                    url = self.reverse(views, *match.args, **match.kwargs)
                except NoReverseMatch:
                    pass
                else:
                    url = urlunsplit((parsed.scheme, parsed.netloc, url, parsed.query, parsed.fragment))
        return url

    @cached_property
    def _callbacks(self):
        return {get_lookup_string(view) for view in self.reverser.views if callable(view)}

    def is_callback(self, view):
        return view in self._callbacks


class Namespace(object):
    def __init__(self, urlpattern, constraints=None, kwargs=None):
        self.urlconf = urlpattern.target
        self.namespace = urlpattern.target.namespace
        self.app_name = urlpattern.target.app_name or urlpattern.target.namespace
        self.constraints = constraints or []
        self.kwargs = kwargs or {}

    def __repr__(self):
        return "<%s '%s' [app_name='%s']>" % (
            self.__class__.__name__, self.urlconf.namespace,
            self.urlconf.app_name,
        )

    def __getitem__(self, item):
        try:
            return self.namespaces[item]
        except KeyError:
            return self.views[item]

    def get_error_message(self, lookup):
        if len(lookup) == 1:
            msg = "'%s' is not a registered view name" % lookup[0]
        else:
            msg = "'%s' is not a registered namespace" % lookup[0]
        if self.app_name:
            msg += " inside '%s'" % self.app_name
        return msg

    def get_views(self, lookup, current_app=None):
        name = lookup[0]
        if len(lookup) == 1:
            return self.views[name]

        current = current_app.pop(0) if current_app else None
        app_name = self.app_dict.get(name, name)
        options = self.namespace_dict[app_name]
        if current and current in options:
            try:
                return self.namespaces[current].get_views(lookup[1:], current_app)
            except KeyError:
                pass
            raise NoReverseMatch(self.get_error_message(lookup))

        if name == app_name and name not in options:
            name = options[0]

        try:
            return self.namespaces[name].get_views(lookup[1:])
        except KeyError:
            pass
        raise NoReverseMatch(self.get_error_message(lookup))

    @cached_property
    def views(self):
        def get_views_recursive(urlpatterns, constraints, kwargs):
            views = defaultdict(list)
            for urlpattern in reversed(urlpatterns):
                constraints = constraints + urlpattern.constraints
                kwargs.push(urlpattern.target.kwargs)
                if urlpattern.is_endpoint():
                    view = View(urlpattern, list(constraints), kwargs.flatten())
                    views[urlpattern.target.view].append(view)
                    if urlpattern.target.url_name:
                        views[urlpattern.target.url_name].append(view)
                elif not urlpattern.target.namespace:
                    for key, value in get_views_recursive(urlpattern.target.urlpatterns, constraints, kwargs).items():
                        views[key].extend(value)
                constraints = constraints[:-len(urlpattern.constraints)]
                kwargs.pop()
            return views

        default_kwargs = BaseContext()
        default_kwargs.dicts[0] = self.kwargs
        return dict(get_views_recursive(self.urlconf.urlpatterns, self.constraints, default_kwargs))

    @cached_property
    def namespaces(self):
        def get_namespaces_recursive(urlpatterns, constraints, kwargs):
            # We need to preserve the order to get the correct default
            # namespace in namespace_dict.
            namespaces = OrderedDict()
            for urlpattern in reversed(urlpatterns):
                if not urlpattern.is_endpoint():
                    constraints = constraints + urlpattern.constraints
                    kwargs.push(urlpattern.target.kwargs)
                    if urlpattern.target.namespace:
                        namespaces[urlpattern.target.namespace] = Namespace(
                            urlpattern, list(constraints),
                            kwargs.flatten(),
                        )
                    else:
                        namespaces.update(
                            get_namespaces_recursive(urlpattern.target.urlpatterns, constraints, kwargs),
                        )
                    constraints = constraints[:-len(urlpattern.constraints)]
                    kwargs.pop()
            return namespaces

        default_kwargs = BaseContext()
        default_kwargs.dicts[0] = self.kwargs
        return get_namespaces_recursive(self.urlconf.urlpatterns, self.constraints, default_kwargs)

    @cached_property
    def namespace_dict(self):
        app_dict = defaultdict(list)
        for namespace in self.namespaces.values():
            app_dict[namespace.app_name].append(namespace.namespace)
        return dict(app_dict)

    @cached_property
    def app_dict(self):
        return {
            namespace.namespace: namespace.app_name
            for namespace in self.namespaces.values()
        }


class View(object):
    def __init__(self, urlpattern, constraints=None, kwargs=None):
        self.endpoint = urlpattern.target
        self.url_name = urlpattern.target.url_name
        self.constraints = constraints or []
        self.kwargs = kwargs or {}

    def __repr__(self):
        return "<%s %s%s>" % (
            self.__class__.__name__, describe_constraints(self.constraints),
            (" [name='%s']" % self.url_name) if self.url_name else '',
        )

    def reverse(self, *args, **kwargs):
        text_args = [force_text(x) for x in args]
        text_kwargs = {k: force_text(v) for k, v in kwargs.items()}

        url = URL()
        new_args, new_kwargs = text_args, text_kwargs
        for constraint in self.constraints:
            url, new_args, new_kwargs = constraint.construct(url, *new_args, **new_kwargs)
        if new_kwargs:
            if any(name not in self.kwargs for name in new_kwargs):
                raise NoReverseMatch()
            for k, v in self.kwargs.items():
                if kwargs.get(k, v) != v:
                    raise NoReverseMatch(self.constraints)
        if new_args:
            raise NoReverseMatch(self.constraints)

        return six.text_type(url)
