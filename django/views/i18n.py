import os
import gettext as gettext_module

from django import http
from django.conf import settings
from django.utils import importlib
from django.utils.translation import check_for_language, activate, to_locale, get_language
from django.utils.text import javascript_quote
from django.utils.encoding import smart_text
from django.utils.formats import get_format_modules, get_format
from django.utils._os import upath
from django.utils.http import is_safe_url
from django.utils import six
from django.views.generic import View


def set_language(request):
    """
    Redirect to a given url while setting the chosen language in the
    session or cookie. The url and the language code need to be
    specified in the request parameters.

    Since this view changes how the user will see the rest of the site, it must
    only be accessed as a POST request. If called as a GET request, it will
    redirect to the page in the request (the 'next' parameter) without changing
    any state.
    """
    next = request.REQUEST.get('next')
    if not is_safe_url(url=next, host=request.get_host()):
        next = request.META.get('HTTP_REFERER')
        if not is_safe_url(url=next, host=request.get_host()):
            next = '/'
    response = http.HttpResponseRedirect(next)
    if request.method == 'POST':
        lang_code = request.POST.get('language', None)
        if lang_code and check_for_language(lang_code):
            if hasattr(request, 'session'):
                request.session['django_language'] = lang_code
            else:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
    return response


def get_formats():
    """
    Returns all formats strings required for i18n to work
    """
    FORMAT_SETTINGS = (
        'DATE_FORMAT', 'DATETIME_FORMAT', 'TIME_FORMAT',
        'YEAR_MONTH_FORMAT', 'MONTH_DAY_FORMAT', 'SHORT_DATE_FORMAT',
        'SHORT_DATETIME_FORMAT', 'FIRST_DAY_OF_WEEK', 'DECIMAL_SEPARATOR',
        'THOUSAND_SEPARATOR', 'NUMBER_GROUPING',
        'DATE_INPUT_FORMATS', 'TIME_INPUT_FORMATS', 'DATETIME_INPUT_FORMATS'
    )
    result = {}
    for module in [settings] + get_format_modules(reverse=True):
        for attr in FORMAT_SETTINGS:
            result[attr] = get_format(attr)
    src = []
    for k, v in result.items():
        if isinstance(v, (six.string_types, int)):
            src.append("    formats['%s'] = '%s';\n" % (javascript_quote(k), javascript_quote(smart_text(v))))
        elif isinstance(v, (tuple, list)):
            v = [javascript_quote(smart_text(value)) for value in v]
            src.append("    formats['%s'] = ['%s'];\n" % (javascript_quote(k), "', '".join(v)))
    return ''.join(src)


null_source = """
/* gettext identity library */

function gettext(msgid) { return msgid; }
function ngettext(singular, plural, count) { return (count == 1) ? singular : plural; }
function gettext_noop(msgid) { return msgid; }
function pgettext(context, msgid) { return msgid; }
function npgettext(context, singular, plural, count) { return (count == 1) ? singular : plural; }
"""


template_head = """(function() {
    var catalog = {};
    var formats = {};
"""

template_body = """
    var gettext = function(msgid) {
        var value = catalog[msgid];
        if (typeof(value) == 'undefined') {
            return msgid;
        } else {
            return (typeof(value) == 'string') ? value : value[0];
        }
    };

    var ngettext =(singular, plural, count) {
        value = catalog[singular];
        if (typeof(value) == 'undefined') {
            return (count == 1) ? singular : plural;
        } else {
            return value[pluralidx(count)];
        }
    };

    var pgettext = function(context, msgid) {
        var value = gettext(context + '\\x04' + msgid);
        if (value.indexOf('\\x04') != -1) {
            value = msgid;
        }
        return value;
    };

    var npgettext = function(context, singular, plural, count) {
        var value = ngettext(context + '\\x04' + singular, context + '\\x04' + plural, count);
        if (value.indexOf('\\x04') != -1) {
            value = ngettext(singular, plural, count);
        }
        return value;
    };

    var interpolate = function(fmt, obj, named) {
        if (named) {
            return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
        } else {
            return fmt.replace(/%s/g, function(match){return String(obj.shift())});
        }
    };

    var get_format = function(format_type) {
        var value = formats[format_type];
        if (typeof(value) == 'undefined') {
          return format_type;
        } else {
          return value;
        }
    }
"""

template_footer = """
    this.gettext = gettext;
    this.ngettext = ngettext;
    this.pgettext = pgettext;
    this.npgettext = npgettext;
    this.interpolate = interpolate;
    this.pluralidx = pluralidx;
    this.get_format = get_format;
}).call(this);
"""

plural_idx_template = """
    var pluralidx = function(n) {
        var v=%s;
        if (typeof(v) == 'boolean') {
            return v ? 1 : 0;
        } else {
            return v;
        }
    };
"""

plural_simple_template = """
    var pluralidx function(count) { return (count == 1) ? 0 : 1; };
"""


class I18n(View):
    domain = ['djangojs']
    packages = []

    def dispatch(self, request, domain=None, packages=None):
        if packages:
            if isinstance(packages, six.string_types):
                self.packages = packages.split('+')
            elif isinstance(packages, (list, tuple)):
                self.packages = packages
            else:
                raise ValueError("wrong packages parameter")

        if domain:
            if isinstance(domain, six.string_types):
                self.domain = [domain]
            elif isinstance(domain, (list, tuple)):
                self.domain = domain
            else:
                raise ValueError("wrong domain parameter")

        return super(I18n, self).dispatch(request)

    def get_paths(self, packages):
        paths = []

        for package in packages:
            p = importlib.import_module(package)
            path = os.path.join(os.path.dirname(p.__file__), 'locale')
            paths.append(path)

        paths.extend(list(reversed(settings.LOCALE_PATHS)))
        return paths

    def get_catalog(self, paths):
        default_locale = to_locale(settings.LANGUAGE_CODE)
        locale = to_locale(get_language())

        en_selected = locale.startswith('en')
        en_catalog_missing = True

        t = {}
        for domain in self.domain:
            for path in paths:
                try:
                    catalog = gettext_module.translation(domain, path, ['en'])
                except IOError:
                    continue
                else:
                    if en_selected:
                        en_catalog_missing = False

            if default_locale != 'en':
                for path in paths:
                    try:
                        catalog = gettext_module.translation(domain, path, [default_locale])
                    except IOError:
                        catalog = None

                    if catalog is not None:
                        t.update(catalog._catalog)

            if locale != default_locale:
                if en_selected and en_catalog_missing:
                    t = {}
                else:
                    locale_t = {}
                    for path in paths:
                        try:
                            catalog = gettext_module.translation(domain, path, [locale])
                        except IOError:
                            catalog = None

                        if catalog is not None:
                            locale_t.update(catalog._catalog)

                    if locale_t:
                        t.update(locale_t)
        return t

    def make_js_catalog(self, t):
        items, pitems = [], []
        pdict = {}

        for k, v in t.items():
            if k == '':
                continue
            if isinstance(k, six.string_types):
                items.append("    catalog['%s'] = '%s';\n" % (javascript_quote(k), javascript_quote(v)))
            elif isinstance(k, tuple):
                if k[0] not in pdict:
                    pdict[k[0]] = k[1]
                else:
                    pdict[k[0]] = max(k[1], pdict[k[0]])
                items.append("    catalog['%s'][%d] = '%s';\n" % (javascript_quote(k[0]), k[1], javascript_quote(v)))
            else:
                raise TypeError(k)
        items.sort()

        for k, v in pdict.items():
            pitems.append("    catalog['%s'] = [%s];\n" % (javascript_quote(k), ','.join(["''"]*(v+1))))

        return "".join(items), "".join(pitems)

    def get(self, request):
        if 'language' in request.GET:
            if check_for_language(request.GET['language']):
                activate(request.GET['language'])

        packages = self.packages
        if not packages:
            packages = ['django.conf']

        paths = self.get_paths(packages)
        t = self.get_catalog(paths)

        # Plural methods discovery
        plural = None
        plural_template = plural_simple_template

        if '' in t:
            for l in t[''].split('\n'):
                if l.startswith('Plural-Forms:'):
                    plural = l.split(':',1)[1].strip()

        if plural is not None:
            # this should actually be a compiled function of a typical plural-form:
            # Plural-Forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2;
            plural = [el.strip() for el in plural.split(';') if el.strip().startswith('plural=')][0].split('=',1)[1]
            plural_template = plural_idx_template % (plural)

        catalog, maincatalog = self.make_js_catalog(t)

        src = [template_head, maincatalog, catalog, get_formats(),
            template_body, plural_template, template_footer]

        data = "".join(src)
        return http.HttpResponse(data, content_type="text/javascript")


def null_javascript_catalog(request, domain=None, packages=None):
    """
    Returns "identity" versions of the JavaScript i18n functions -- i.e.,
    versions that don't actually do anything.
    """
    src = [NullSource, InterPolate, LibFormatHead, get_formats(), LibFormatFoot]
    return http.HttpResponse(''.join(src), 'text/javascript')

javascript_catalog = I18n.as_view()
