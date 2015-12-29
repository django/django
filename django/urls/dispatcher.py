from collections import defaultdict
from importlib import import_module

from django.conf import urls
from django.template.context import BaseContext
from django.utils import lru_cache, six
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit
from django.utils.translation import override

from .constraints import ScriptPrefix
from .exceptions import NoReverseMatch, Resolver404
from .resolvers import get_resolver
from .utils import URL, get_callable


@lru_cache.lru_cache(maxsize=None)
def get_dispatcher(urlconf=None):
    if urlconf is None:
        from django.conf import settings
        urlconf = settings.ROOT_URLCONF
    return Dispatcher(urlconf)


class Dispatcher(object):
    def __init__(self, urlconf):
        self.ready = False
        self.urlconf_name = urlconf
        self.resolver = get_resolver(urlconf)

        self._namespaces = {}
        self._loaded = set()
        self._callbacks = set()
        self.reverse_dict = MultiValueDict()
        self.app_dict = defaultdict(list)

        self.load_root()

    def _load(self, root, namespace_root, app_root, constraints, kwargs):
        for pattern in reversed(root.target.urlconf.urlpatterns):
            constraints += pattern.constraints
            kwargs.push(pattern.target.kwargs)
            if pattern.is_view():
                value = list(constraints), kwargs.flatten()
                self.reverse_dict.appendlist(namespace_root + (pattern.target.view,), value)
                if pattern.target.name:
                    self.reverse_dict.appendlist(namespace_root + (pattern.target.name,), value)
                self._callbacks.add(pattern.target.lookup_str)
            elif not pattern.target.namespace and not pattern.target.app_name:
                self._load(pattern, namespace_root, app_root, list(constraints), kwargs)
            else:
                app_name = app_root + (pattern.target.app_name or pattern.target.namespace,)
                self.app_dict[app_name].append(pattern.target.namespace)
                self._namespaces[namespace_root + (pattern.target.namespace,)] = (
                    app_name,
                    urls.URLPattern(list(constraints), urls.Include(
                        urls.URLConf(list(pattern.target.urlconf.urlpatterns), pattern.target.app_name),
                        namespace=pattern.target.namespace,
                        kwargs=kwargs.flatten(),
                    ))
                )
            constraints = constraints[:-len(pattern.constraints)]
            kwargs.pop()

    def load(self, namespace_root):
        if namespace_root not in self._namespaces:
            raise NoReverseMatch(
                "%s is not a registered namespace inside '%s'" %
                (namespace_root[-1], ':'.join(namespace_root[:-1]))
            )

        app_root, pattern = self._namespaces.pop(namespace_root)
        constraints = list(pattern.constraints)
        kwargs = BaseContext()
        kwargs.dicts[0] = pattern.target.kwargs
        self._load(pattern, namespace_root, app_root, constraints, kwargs)
        self._loaded.add(namespace_root)

    def load_root(self):
        self._namespaces[()] = (), urls.URLPattern([ScriptPrefix()], urls.Include(urls.URLConf(self.urlconf_name)))
        self.load(())
        self.ready = True

    def load_namespace(self, namespace):
        for i, _ in enumerate(namespace, start=1):
            if namespace[:i] not in self._loaded:
                self.load(namespace[:i])

    def resolve(self, path, request=None):
        return self.resolver.resolve(path, request)

    def reverse(self, viewname, *args, **kwargs):
        if isinstance(viewname, (list, tuple)):
            lookup = tuple(viewname)
        elif isinstance(viewname, six.string_types):
            lookup = tuple(viewname.split(':'))
        elif viewname:
            lookup = (viewname,)
        else:
            raise NoReverseMatch()

        text_args = [force_text(x) for x in args]
        text_kwargs = {k: force_text(v) for k, v in kwargs.items()}

        self.load_namespace(lookup[:-1])

        patterns = []
        for value in self.reverse_dict.getlist(lookup):
            constraints, default_kwargs = value
            url = URL()
            new_args, new_kwargs = text_args, text_kwargs
            try:
                for constraint in constraints:
                    url, new_args, new_kwargs = constraint.construct(url, *new_args, **new_kwargs)
                if new_kwargs:
                    if any(name not in default_kwargs for name in new_kwargs):
                        raise NoReverseMatch()
                    for k, v in default_kwargs.items():
                        if kwargs.get(k, v) != v:
                            raise NoReverseMatch()
                if new_args:
                    raise NoReverseMatch()
            except NoReverseMatch:
                # We don't need the leading slash of the root pattern here
                patterns.append(constraints[1:])
            else:
                return six.text_type(url)

        if lookup and isinstance(lookup[-1], six.string_types):
            viewname = ':'.join(lookup)

        raise NoReverseMatch(
            "Reverse for '%s' with arguments '%s' and keyword "
            "arguments '%s' not found. %d pattern(s) tried: %s" %
            (
                viewname, args, kwargs, len(patterns),
                [str('').join(c.describe() for c in constraints) for constraints in patterns],
            )
        )

    def _resolve_lookup(self, root, lookup, current_app=None):
        if len(lookup) == 1:
            return lookup

        self.load_namespace(root)

        ns = lookup[0]
        app = current_app[0] if current_app else None
        root = root + (ns,)
        options = self.app_dict[root]
        if app and app in options:
            namespace = app
        elif ns in options:
            namespace = ns
            current_app = []
        elif options:
            namespace = options[0]
            current_app = []
        else:
            namespace = ns
            current_app = []

        return [namespace] + self._resolve_lookup(root, lookup[1:], current_app[1:])

    @lru_cache.lru_cache(maxsize=None)
    def _resolve_namespace(self, lookup, current_app):
        lookup = list(lookup)
        if current_app is not None:
            current_app = list(current_app)
        return self._resolve_lookup((), lookup, current_app)

    def resolve_namespace(self, viewname, current_app=None):
        if isinstance(viewname, six.string_types):
            lookup = viewname.split(':')
        elif viewname:
            lookup = [viewname]
        else:
            return []

        if current_app:
            current_app = current_app.split(':')

        lookup = tuple(lookup)
        current_app = tuple(current_app) if current_app is not None else ()
        return self._resolve_namespace(lookup, current_app)

    @cached_property
    def urlconf_module(self):
        if isinstance(self.urlconf_name, six.string_types):
            return import_module(self.urlconf_name)
        else:
            return self.urlconf_name

    def _is_callback(self, name):
        return name in self._callbacks

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
            to_be_reversed = match.namespaces + [match.url_name]
            with override(lang_code):
                try:
                    url = self.reverse(to_be_reversed, *match.args, **match.kwargs)
                except NoReverseMatch:
                    pass
                else:
                    url = urlunsplit((parsed.scheme, parsed.netloc, url, parsed.query, parsed.fragment))
        return url
