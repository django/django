# coding: utf-8

ur"""
Format string interpolation should work with *_lazy objects.

>>> from django.utils.translation import ugettext_lazy, activate, deactivate, gettext_lazy
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
"""
