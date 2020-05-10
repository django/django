import itertools
import json
import os
import re
from urllib.parse import unquote

from django.apps import apps
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context, Engine
from django.urls import translate_url
from django.utils.formats import get_format
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import (
    LANGUAGE_SESSION_KEY, check_for_language, get_language,
)
from django.utils.translation.trans_real import DjangoTranslation
from django.views.generic import View

LANGUAGE_QUERY_PARAMETER = 'language'


def set_language(request):
    """
    Redirect to a given URL while setting the chosen language in the session
    (if enabled) and in a cookie. The URL and the language code need to be
    specified in the request parameters.

    Since this view changes how the user will see the rest of the site, it must
    only be accessed as a POST request. If called as a GET request, it will
    redirect to the page in the request (the 'next' parameter) without changing
    any state.
    """
    next_url = request.POST.get('next', request.GET.get('next'))
    if (
        (next_url or request.accepts('text/html')) and
        not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
    ):
        next_url = request.META.get('HTTP_REFERER')
        # HTTP_REFERER may be encoded.
        next_url = next_url and unquote(next_url)
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = '/'
    response = HttpResponseRedirect(next_url) if next_url else HttpResponse(status=204)
    if request.method == 'POST':
        lang_code = request.POST.get(LANGUAGE_QUERY_PARAMETER)
        if lang_code and check_for_language(lang_code):
            if next_url:
                next_trans = translate_url(next_url, lang_code)
                if next_trans != next_url:
                    response = HttpResponseRedirect(next_trans)
            if hasattr(request, 'session'):
                # Storing the language in the session is deprecated.
                # (RemovedInDjango40Warning)
                request.session[LANGUAGE_SESSION_KEY] = lang_code
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME, lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
    return response


def get_formats():
    """Return all formats strings required for i18n to work."""
    FORMAT_SETTINGS = (
        'DATE_FORMAT', 'DATETIME_FORMAT', 'TIME_FORMAT',
        'YEAR_MONTH_FORMAT', 'MONTH_DAY_FORMAT', 'SHORT_DATE_FORMAT',
        'SHORT_DATETIME_FORMAT', 'FIRST_DAY_OF_WEEK', 'DECIMAL_SEPARATOR',
        'THOUSAND_SEPARATOR', 'NUMBER_GROUPING',
        'DATE_INPUT_FORMATS', 'TIME_INPUT_FORMATS', 'DATETIME_INPUT_FORMATS'
    )
    return {attr: get_format(attr) for attr in FORMAT_SETTINGS}


js_catalog_template = r"""
{% autoescape off %}
(function(globals) {

  var django = globals.django || (globals.django = {});

  {% if plural %}
  django.pluralidx = function(n) {
    var v={{ plural }};
    if (typeof(v) == 'boolean') {
      return v ? 1 : 0;
    } else {
      return v;
    }
  };
  {% else %}
  django.pluralidx = function(count) { return (count == 1) ? 0 : 1; };
  {% endif %}

  /* gettext library */

  django.catalog = django.catalog || {};
  {% if catalog_str %}
  var newcatalog = {{ catalog_str }};
  for (var key in newcatalog) {
    django.catalog[key] = newcatalog[key];
  }
  {% endif %}

  if (!django.jsi18n_initialized) {
    django.gettext = function(msgid) {
      var value = django.catalog[msgid];
      if (typeof(value) == 'undefined') {
        return msgid;
      } else {
        return (typeof(value) == 'string') ? value : value[0];
      }
    };

    django.ngettext = function(singular, plural, count) {
      var value = django.catalog[singular];
      if (typeof(value) == 'undefined') {
        return (count == 1) ? singular : plural;
      } else {
        return value.constructor === Array ? value[django.pluralidx(count)] : value;
      }
    };

    django.gettext_noop = function(msgid) { return msgid; };

    django.pgettext = function(context, msgid) {
      var value = django.gettext(context + '\x04' + msgid);
      if (value.indexOf('\x04') != -1) {
        value = msgid;
      }
      return value;
    };

    django.npgettext = function(context, singular, plural, count) {
      var value = django.ngettext(context + '\x04' + singular, context + '\x04' + plural, count);
      if (value.indexOf('\x04') != -1) {
        value = django.ngettext(singular, plural, count);
      }
      return value;
    };

    django.interpolate = function(fmt, obj, named) {
      if (named) {
        return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
      } else {
        return fmt.replace(/%s/g, function(match){return String(obj.shift())});
      }
    };


    /* formatting library */

    django.formats = {{ formats_str }};

    django.get_format = function(format_type) {
      var value = django.formats[format_type];
      if (typeof(value) == 'undefined') {
        return format_type;
      } else {
        return value;
      }
    };

    /* add to global namespace */
    globals.pluralidx = django.pluralidx;
    globals.gettext = django.gettext;
    globals.ngettext = django.ngettext;
    globals.gettext_noop = django.gettext_noop;
    globals.pgettext = django.pgettext;
    globals.npgettext = django.npgettext;
    globals.interpolate = django.interpolate;
    globals.get_format = django.get_format;

    django.jsi18n_initialized = true;
  }

}(this));
{% endautoescape %}
"""


class JavaScriptCatalog(View):
    """
    Return the selected language catalog as a JavaScript library.

    Receive the list of packages to check for translations in the `packages`
    kwarg either from the extra dictionary passed to the path() function or as
    a plus-sign delimited string from the request. Default is 'django.conf'.

    You can override the gettext domain for this view, but usually you don't
    want to do that as JavaScript messages go to the djangojs domain. This
    might be needed if you deliver your JavaScript source from Django templates.
    """
    domain = 'djangojs'
    packages = None

    def get(self, request, *args, **kwargs):
        locale = get_language()
        domain = kwargs.get('domain', self.domain)
        # If packages are not provided, default to all installed packages, as
        # DjangoTranslation without localedirs harvests them all.
        packages = kwargs.get('packages', '')
        packages = packages.split('+') if packages else self.packages
        paths = self.get_paths(packages) if packages else None
        self.translation = DjangoTranslation(locale, domain=domain, localedirs=paths)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_paths(self, packages):
        allowable_packages = {app_config.name: app_config for app_config in apps.get_app_configs()}
        app_configs = [allowable_packages[p] for p in packages if p in allowable_packages]
        if len(app_configs) < len(packages):
            excluded = [p for p in packages if p not in allowable_packages]
            raise ValueError(
                'Invalid package(s) provided to JavaScriptCatalog: %s' % ','.join(excluded)
            )
        # paths of requested packages
        return [os.path.join(app.path, 'locale') for app in app_configs]

    @property
    def _num_plurals(self):
        """
        Return the number of plurals for this catalog language, or 2 if no
        plural string is available.
        """
        match = re.search(r'nplurals=\s*(\d+)', self._plural_string or '')
        if match:
            return int(match[1])
        return 2

    @property
    def _plural_string(self):
        """
        Return the plural string (including nplurals) for this catalog language,
        or None if no plural string is available.
        """
        if '' in self.translation._catalog:
            for line in self.translation._catalog[''].split('\n'):
                if line.startswith('Plural-Forms:'):
                    return line.split(':', 1)[1].strip()
        return None

    def get_plural(self):
        plural = self._plural_string
        if plural is not None:
            # This should be a compiled function of a typical plural-form:
            # Plural-Forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 :
            #               n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2;
            plural = [el.strip() for el in plural.split(';') if el.strip().startswith('plural=')][0].split('=', 1)[1]
        return plural

    def get_catalog(self):
        pdict = {}
        num_plurals = self._num_plurals
        catalog = {}
        trans_cat = self.translation._catalog
        trans_fallback_cat = self.translation._fallback._catalog if self.translation._fallback else {}
        seen_keys = set()
        for key, value in itertools.chain(trans_cat.items(), trans_fallback_cat.items()):
            if key == '' or key in seen_keys:
                continue
            if isinstance(key, str):
                catalog[key] = value
            elif isinstance(key, tuple):
                msgid, cnt = key
                pdict.setdefault(msgid, {})[cnt] = value
            else:
                raise TypeError(key)
            seen_keys.add(key)
        for k, v in pdict.items():
            catalog[k] = [v.get(i, '') for i in range(num_plurals)]
        return catalog

    def get_context_data(self, **kwargs):
        return {
            'catalog': self.get_catalog(),
            'formats': get_formats(),
            'plural': self.get_plural(),
        }

    def render_to_response(self, context, **response_kwargs):
        def indent(s):
            return s.replace('\n', '\n  ')

        template = Engine().from_string(js_catalog_template)
        context['catalog_str'] = indent(
            json.dumps(context['catalog'], sort_keys=True, indent=2)
        ) if context['catalog'] else None
        context['formats_str'] = indent(json.dumps(context['formats'], sort_keys=True, indent=2))

        return HttpResponse(template.render(Context(context)), 'text/javascript; charset="utf-8"')


class JSONCatalog(JavaScriptCatalog):
    """
    Return the selected language catalog as a JSON object.

    Receive the same parameters as JavaScriptCatalog and return a response
    with a JSON object of the following format:

        {
            "catalog": {
                # Translations catalog
            },
            "formats": {
                # Language formats for date, time, etc.
            },
            "plural": '...'  # Expression for plural forms, or null.
        }
    """
    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(context)
