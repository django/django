from django import http
from django.utils.translation import check_for_language, activate, to_locale, get_language
from django.utils.text import javascript_quote
from django.conf import settings
import os
import gettext as gettext_module

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
    return http.HttpResponse(NullSource + InterPolate, 'text/javascript')

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
    if type(packages) in (str, unicode):
        packages = packages.split('+')
    packages = [p for p in packages if p == 'django.conf' or p in settings.INSTALLED_APPS]
    default_locale = to_locale(settings.LANGUAGE_CODE)
    locale = to_locale(get_language())
    t = {}
    paths = []
    # first load all english languages files for defaults
    for package in packages:
        p = __import__(package, {}, {}, [''])
        path = os.path.join(os.path.dirname(p.__file__), 'locale')
        paths.append(path)
        try:
            catalog = gettext_module.translation(domain, path, ['en'])
            t.update(catalog._catalog)
        except IOError:
            # 'en' catalog was missing. This is harmless.
            pass
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
        for path in paths:
            try:
                catalog = gettext_module.translation(domain, path, [locale])
            except IOError:
                catalog = None
            if catalog is not None:
                t.update(catalog._catalog)
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
        if type(k) in (str, unicode):
            csrc.append("catalog['%s'] = '%s';\n" % (javascript_quote(k), javascript_quote(v)))
        elif type(k) == tuple:
            if k[0] not in pdict:
                pdict[k[0]] = k[1]
            else:
                pdict[k[0]] = max(k[1], pdict[k[0]])
            csrc.append("catalog['%s'][%d] = '%s';\n" % (javascript_quote(k[0]), k[1], javascript_quote(v)))
        else:
            raise TypeError, k
    csrc.sort()
    for k,v in pdict.items():
        src.append("catalog['%s'] = [%s];\n" % (javascript_quote(k), ','.join(["''"]*(v+1))))
    src.extend(csrc)
    src.append(LibFoot)
    src.append(InterPolate)
    src = ''.join(src)
    return http.HttpResponse(src, 'text/javascript')
