import os
import gettext as gettext_module

from django import http
from django.conf import settings
from django.utils import importlib
from django.utils.translation import check_for_language, activate, to_locale, get_language
from django.utils.text import javascript_quote
from django.utils.encoding import smart_unicode
from django.utils.formats import get_format_modules, get_format

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
    next = request.REQUEST.get('next', None)
    if not next:
        next = request.META.get('HTTP_REFERER', None)
    if not next:
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
        if isinstance(v, (basestring, int)):
            src.append("formats['%s'] = '%s';\n" % (javascript_quote(k), javascript_quote(smart_unicode(v))))
        elif isinstance(v, (tuple, list)):
            v = [javascript_quote(smart_unicode(value)) for value in v]
            src.append("formats['%s'] = ['%s'];\n" % (javascript_quote(k), "', '".join(v)))
    return ''.join(src)

NullSource = """
/* gettext identity library */

function gettext(msgid) { return msgid; }
function ngettext(singular, plural, count) { return (count == 1) ? singular : plural; }
function gettext_noop(msgid) { return msgid; }
"""

LibHead = """
/* gettext library */

var catalog = new Array();
"""

LibFoot = """

function gettext(msgid) {
  var value = catalog[msgid];
  if (typeof(value) == 'undefined') {
    return msgid;
  } else {
    return (typeof(value) == 'string') ? value : value[0];
  }
}

function ngettext(singular, plural, count) {
  value = catalog[singular];
  if (typeof(value) == 'undefined') {
    return (count == 1) ? singular : plural;
  } else {
    return value[pluralidx(count)];
  }
}

function gettext_noop(msgid) { return msgid; }

"""

LibFormatHead = """
/* formatting library */

var formats = new Array();

"""

LibFormatFoot = """
function get_format(format_type) {
    var value = formats[format_type];
    if (typeof(value) == 'undefined') {
      return msgid;
    } else {
      return value;
    }
}
"""

SimplePlural = """
function pluralidx(count) { return (count == 1) ? 0 : 1; }
"""

InterPolate = r"""
function interpolate(fmt, obj, named) {
  if (named) {
    return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
  } else {
    return fmt.replace(/%s/g, function(match){return String(obj.shift())});
  }
}
"""

PluralIdx = r"""
function pluralidx(n) {
  var v=%s;
  if (typeof(v) == 'boolean') {
    return v ? 1 : 0;
  } else {
    return v;
  }
}
"""

def null_javascript_catalog(request, domain=None, packages=None):
    """
    Returns "identity" versions of the JavaScript i18n functions -- i.e.,
    versions that don't actually do anything.
    """
    src = [NullSource, InterPolate, LibFormatHead, get_formats(), LibFormatFoot]
    return http.HttpResponse(''.join(src), 'text/javascript')

def javascript_catalog(request, domain='djangojs', packages=None):
    """
    Returns the selected language catalog as a javascript library.

    Receives the list of packages to check for translations in the
    packages parameter either from an infodict or as a +-delimited
    string from the request. Default is 'django.conf'.

    Additionally you can override the gettext domain for this view,
    but usually you don't want to do that, as JavaScript messages
    go to the djangojs domain. But this might be needed if you
    deliver your JavaScript source from Django templates.
    """
    if request.GET:
        if 'language' in request.GET:
            if check_for_language(request.GET['language']):
                activate(request.GET['language'])
    if packages is None:
        packages = ['django.conf']
    if isinstance(packages, basestring):
        packages = packages.split('+')
    packages = [p for p in packages if p == 'django.conf' or p in settings.INSTALLED_APPS]
    default_locale = to_locale(settings.LANGUAGE_CODE)
    locale = to_locale(get_language())
    t = {}
    paths = []
    en_selected = locale.startswith('en')
    en_catalog_missing = True
    # first load all english languages files for defaults
    for package in packages:
        p = importlib.import_module(package)
        path = os.path.join(os.path.dirname(p.__file__), 'locale')
        paths.append(path)
        try:
            catalog = gettext_module.translation(domain, path, ['en'])
            t.update(catalog._catalog)
        except IOError:
            pass
        else:
            # 'en' is the selected language and at least one of the packages
            # listed in `packages` has an 'en' catalog
            if en_selected:
                en_catalog_missing = False
    # next load the settings.LANGUAGE_CODE translations if it isn't english
    if default_locale != 'en':
        for path in paths:
            try:
                catalog = gettext_module.translation(domain, path, [default_locale])
            except IOError:
                catalog = None
            if catalog is not None:
                t.update(catalog._catalog)
    # last load the currently selected language, if it isn't identical to the default.
    if locale != default_locale:
        # If the currently selected language is English but it doesn't have a
        # translation catalog (presumably due to being the language translated
        # from) then a wrong language catalog might have been loaded in the
        # previous step. It needs to be discarded.
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
                t = locale_t
    src = [LibHead]
    plural = None
    if '' in t:
        for l in t[''].split('\n'):
            if l.startswith('Plural-Forms:'):
                plural = l.split(':',1)[1].strip()
    if plural is not None:
        # this should actually be a compiled function of a typical plural-form:
        # Plural-Forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2;
        plural = [el.strip() for el in plural.split(';') if el.strip().startswith('plural=')][0].split('=',1)[1]
        src.append(PluralIdx % plural)
    else:
        src.append(SimplePlural)
    csrc = []
    pdict = {}
    for k, v in t.items():
        if k == '':
            continue
        if isinstance(k, basestring):
            csrc.append("catalog['%s'] = '%s';\n" % (javascript_quote(k), javascript_quote(v)))
        elif isinstance(k, tuple):
            if k[0] not in pdict:
                pdict[k[0]] = k[1]
            else:
                pdict[k[0]] = max(k[1], pdict[k[0]])
            csrc.append("catalog['%s'][%d] = '%s';\n" % (javascript_quote(k[0]), k[1], javascript_quote(v)))
        else:
            raise TypeError(k)
    csrc.sort()
    for k, v in pdict.items():
        src.append("catalog['%s'] = [%s];\n" % (javascript_quote(k), ','.join(["''"]*(v+1))))
    src.extend(csrc)
    src.append(LibFoot)
    src.append(InterPolate)
    src.append(LibFormatHead)
    src.append(get_formats())
    src.append(LibFormatFoot)
    src = ''.join(src)
    return http.HttpResponse(src, 'text/javascript')

