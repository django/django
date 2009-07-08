# coding: utf-8
import misc

regressions = ur"""
Format string interpolation should work with *_lazy objects.

>>> from django.utils.translation import ugettext, ugettext_lazy, activate, deactivate, gettext_lazy
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

Localization of dates and numbers

>>> import datetime
>>> import decimal
>>> from django.utils.formats import getformat, date_format, number_format, localize

>>> n = decimal.Decimal('66666.666')
>>> d = datetime.date(2009, 7, 6)
>>> dt = datetime.datetime(2009, 7, 6, 20, 50)

Locale independent

>>> number_format(n, decimal_sep='.', decimal_pos=2, grouping=3, thousand_sep=',')
'66,666.66'
>>> number_format(n, decimal_sep='A', decimal_pos=1, grouping=1, thousand_sep='B')
'6B6B6B6B6BA6'

English locale

>>> activate('en')
>>> getformat('DATE_FORMAT')
'N j, Y'
>>> getformat('FIRST_DAY_OF_WEEK')
0
>>> getformat('DECIMAL_SEPARATOR')
'.'
>>> date_format(d)
'July 6, 2009'
>>> date_format(d, 'YEAR_MONTH_FORMAT')
'July 2009'
>>> date_format(d, 'SHORT_DATETIME_FORMAT')
'07/06/2009 8:50 p.m.'
>>> localize('No localizable')
'No localizable'
>>> localize(n)
'66666.666'
>>> localize(d)
'July 6, 2009'
>>> localize(dt)
'July 6, 2009, 8:50 p.m.'

Catalan locale

>>> activate('ca')
>>> getformat('DATE_FORMAT')
'j \de N \de Y'
>>> getformat('FIRST_DAY_OF_WEEK')
1
>>> getformat('DECIMAL_SEPARATOR')
','
>>> date_format(d)
'6 de juliol de 2009'
>>> date_format(d, 'YEAR_MONTH_FORMAT')
'juliol de 2009'
>>> date_format(d, 'SHORT_DATETIME_FORMAT')
'06/07/2009 20:50'
>>> localize('No localizable')
'No localizable'
>>> localize(n)
'66.666,666'
>>> localize(d)
'6 de juliol de 2009'
>>> localize(dt)
'6 de juliol de 2009 a les 20:50'

"""

__test__ = {
    'regressions': regressions,
    'misc': misc.tests,
}
