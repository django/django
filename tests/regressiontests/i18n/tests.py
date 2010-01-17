# coding: utf-8
import misc

regressions = ur"""
Format string interpolation should work with *_lazy objects.

>>> from django.utils.translation import ugettext, ugettext_lazy, activate, deactivate, gettext_lazy, to_locale
>>> s = ugettext_lazy('Add %(name)s')
>>> d = {'name': 'Ringo'}
>>> s % d
u'Add Ringo'
>>> activate('de')
>>> s % d
u'Ringo hinzuf\xfcgen'
>>> activate('pl')
>>> s % d
u'Dodaj Ringo'
>>> deactivate()

Tests the to_locale function and the special case of Serbian Latin (refs #12230 and r11299)

>>> to_locale('en-us')
'en_US'
>>> to_locale('sr-lat')
'sr_Lat'

Test the to_language function

>>> from django.utils.translation.trans_real import to_language
>>> to_language('en_US')
'en-us'
>>> to_language('sr_Lat')
'sr-lat'

It should be possible to compare *_lazy objects.

>>> s1 = ugettext_lazy('Add %(name)s')
>>> s == s1
True
>>> s2 = gettext_lazy('Add %(name)s')
>>> s3 = gettext_lazy('Add %(name)s')
>>> s2 == s3
True
>>> s == s2
True
>>> s4 = ugettext_lazy('Some other string')
>>> s == s4
False

unicode(string_concat(...)) should not raise a TypeError - #4796

>>> import django.utils.translation
>>> reload(django.utils.translation)
<module 'django.utils.translation' from ...>
>>> unicode(django.utils.translation.string_concat("dja", "ngo"))
u'django'

Translating a string requiring no auto-escaping shouldn't change the "safe"
status.

>>> from django.utils.safestring import mark_safe, SafeString
>>> s = mark_safe('Password')
>>> type(s)
<class 'django.utils.safestring.SafeString'>
>>> activate('de')
>>> type(ugettext(s))
<class 'django.utils.safestring.SafeUnicode'>
>>> deactivate()

>>> SafeString('a') + s
'aPassword'
>>> s + SafeString('a')
'Passworda'
>>> s + mark_safe('a')
'Passworda'
>>> mark_safe('a') + s
'aPassword'
>>> mark_safe('a') + mark_safe('s')
'as'
>>> print s
Password
"""

__test__ = {
    'regressions': regressions,
    'misc': misc.tests,
}
