import sys

tests = """
>>> from django.utils.translation.trans_real import parse_accept_lang_header
>>> p = parse_accept_lang_header

#
# Testing HTTP header parsing. First, we test that we can parse the values
# according to the spec (and that we extract all the pieces in the right order).
#

Good headers.
>>> p('de')
[('de', 1.0)]
>>> p('en-AU')
[('en-AU', 1.0)]
>>> p('*;q=1.00')
[('*', 1.0)]
>>> p('en-AU;q=0.123')
[('en-AU', 0.123)]
>>> p('en-au;q=0.5')
[('en-au', 0.5)]
>>> p('en-au;q=1.0')
[('en-au', 1.0)]
>>> p('da, en-gb;q=0.25, en;q=0.5')
[('da', 1.0), ('en', 0.5), ('en-gb', 0.25)]
>>> p('en-au-xx')
[('en-au-xx', 1.0)]
>>> p('de,en-au;q=0.75,en-us;q=0.5,en;q=0.25,es;q=0.125,fa;q=0.125')
[('de', 1.0), ('en-au', 0.75), ('en-us', 0.5), ('en', 0.25), ('es', 0.125), ('fa', 0.125)]
>>> p('*')
[('*', 1.0)]
>>> p('de;q=0.')
[('de', 1.0)]
>>> p('')
[]

Bad headers; should always return [].
>>> p('en-gb;q=1.0000')
[]
>>> p('en;q=0.1234')
[]
>>> p('en;q=.2')
[]
>>> p('abcdefghi-au')
[]
>>> p('**')
[]
>>> p('en,,gb')
[]
>>> p('en-au;q=0.1.0')
[]
>>> p('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXZ,en')
[]
>>> p('da, en-gb;q=0.8, en;q=0.7,#')
[]
>>> p('de;q=2.0')
[]
>>> p('de;q=0.a')
[]
>>> p('')
[]

#
# Now test that we parse a literal HTTP header correctly.
#

>>> from django.utils.translation.trans_real import get_language_from_request
>>> g = get_language_from_request
>>> from django.http import HttpRequest
>>> r = HttpRequest
>>> r.COOKIES = {}

These tests assumes the es, es_AR, pt and pt_BR translations exit in the Django
source tree.
>>> r.META = {'HTTP_ACCEPT_LANGUAGE': 'pt-br'}
>>> g(r)
'pt-br'
>>> r.META = {'HTTP_ACCEPT_LANGUAGE': 'pt'}
>>> g(r)
'pt'
>>> r.META = {'HTTP_ACCEPT_LANGUAGE': 'es,de'}
>>> g(r)
'es'
>>> r.META = {'HTTP_ACCEPT_LANGUAGE': 'es-ar,de'}
>>> g(r)
'es-ar'

# Now test that we parse language preferences stored in a cookie correctly.
>>> from django.conf import settings
>>> r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'pt-br'}
>>> r.META = {}
>>> g(r)
'pt-br'
>>> r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'pt'}
>>> r.META = {}
>>> g(r)
'pt'
>>> r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'es'}
>>> r.META = {'HTTP_ACCEPT_LANGUAGE': 'de'}
>>> g(r)
'es'
"""

# Python 2.3 and 2.4 return slightly different results for completely bogus
# locales, so we omit this test for that anything below 2.4. It's relatively
# harmless in any cases (GIGO). This also means this won't be executed on
# Jython currently, but life's like that sometimes. (On those platforms,
# passing in a truly bogus locale will get you the default locale back.)
if sys.version_info >= (2, 5):
    tests += """
This test assumes there won't be a Django translation to a US variation
of the Spanish language, a safe assumption. When the user sets it
as the preferred language, the main 'es' translation should be selected
instead.
>>> r.COOKIES = {}
>>> r.META = {'HTTP_ACCEPT_LANGUAGE': 'es-us'}
>>> g(r)
'es'
>>> r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'es-us'}
>>> r.META = {}
>>> g(r)
'es'
"""

tests += """
This tests the following scenario: there isn't a main language (zh)
translation of Django but there is a translation to variation (zh_CN)
the user sets zh-cn as the preferred language, it should be selected by
Django without falling back nor ignoring it.
>>> r.COOKIES = {}
>>> r.META = {'HTTP_ACCEPT_LANGUAGE': 'zh-cn,de'}
>>> g(r)
'zh-cn'
>>> r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'zh-cn'}
>>> r.META = {'HTTP_ACCEPT_LANGUAGE': 'de'}
>>> g(r)
'zh-cn'
"""
