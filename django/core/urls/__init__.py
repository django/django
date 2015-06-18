from __future__ import unicode_literals
import warnings
from django.core.exceptions import ImproperlyConfigured

from django.utils import lru_cache, six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_text
from django.utils.functional import lazy
from django.utils.http import urlquote, RFC3986_SUBDELIMS

from .resolvers import Resolver, ResolverEndpoint, ResolverMatch  # NOQA
from .exceptions import NoReverseMatch, Resolver404  # NOQA
from .utils import URL  # NOQA
from .constraints import RegexPattern


@lru_cache.lru_cache(maxsize=None)
def get_resolver(urlconf):
    if urlconf is None:
        from django.conf import settings
        urlconf = settings.ROOT_URLCONF
    return Resolver(urlconf, constraints=[RegexPattern(r'^/')])


def resolve(path, urlconf=None, request=None):
    path = force_text(path)
    if urlconf is None:
        from django.core.urlresolvers import get_urlconf
        urlconf = get_urlconf()
    return get_resolver(urlconf).resolve(path, request)


def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None, strings_only=True):
    if urlconf is None:
        from django.core.urlresolvers import get_urlconf
        urlconf = get_urlconf()

    resolver = get_resolver(urlconf)
    args = args or []
    text_args = [force_text(x) for x in args]
    kwargs = kwargs or {}
    text_kwargs = {k: force_text(v) for k, v in kwargs.items()}

    from django.core.urlresolvers import get_script_prefix
    prefix = get_script_prefix()[:-1]

    if isinstance(viewname, six.string_types):
        original_lookup = viewname.split(':')
    else:
        original_lookup = [viewname]

    current_app = current_app.split(':') if current_app else []

    lookup = resolver.resolve_namespace(original_lookup, current_app)

    for constraints, default_kwargs in resolver.search(lookup):
        url = URL()
        new_args, new_kwargs = text_args, text_kwargs
        try:
            for constraint in constraints:
                url, new_args, new_kwargs = constraint.construct(url, new_args, new_kwargs)
            if new_kwargs:
                if any(name not in default_kwargs for name in new_kwargs):
                    raise NoReverseMatch()
                for k, v in default_kwargs.items():
                    if kwargs.get(k, v) != v:
                        raise NoReverseMatch()
            if new_args:
                raise NoReverseMatch()
        except NoReverseMatch:
            pass
        else:
            url.path = urlquote(prefix + url.path, safe=RFC3986_SUBDELIMS + str('/~:@'))
            # url.path = prefix + url.path
            if url.path.startswith('//'):
                url.path = '/%%2F%s' % url.path[2:]
            return force_text(url) if strings_only else url

    raise NoReverseMatch()


reverse_lazy = lazy(reverse, URL)


def url(constraints, view, kwargs=None, name=None, prefix=''):
    if isinstance(constraints, six.string_types):
        constraints = RegexPattern(constraints)
    if not isinstance(constraints, (list, tuple)):
        constraints = [constraints]

    if isinstance(view, (list, tuple)):
        resolvers, app_name, namespace = view
        return namespace, Resolver(resolvers, app_name, constraints=constraints, default_kwargs=kwargs)
    else:
        if isinstance(view, six.string_types):
            warnings.warn(
                'Support for string view arguments to url() is deprecated and '
                'will be removed in Django 2.0 (got %s). Pass the callable '
                'instead.' % view,
                RemovedInDjango20Warning, stacklevel=2
            )
            if not view:
                raise ImproperlyConfigured('Empty URL pattern view name not permitted (for pattern %r)' % constraints)
            if prefix:
                view = prefix + '.' + view
        return None, ResolverEndpoint(view, name, constraints=constraints, default_kwargs=kwargs)