# -*- coding: utf-8 -*-
"""
An alphabetical list of Swedish counties, sorted by codes.

http://en.wikipedia.org/wiki/Counties_of_Sweden

This exists in this standalone file so that it's only imported into memory
when explicitly needed.

"""

from django.utils.translation import ugettext_lazy as _

COUNTY_CHOICES = (
    ('AB', _(u'Stockholm')),
    ('AC', _(u'Västerbotten')),
    ('BD', _(u'Norrbotten')),
    ('C', _(u'Uppsala')),
    ('D', _(u'Södermanland')),
    ('E', _(u'Östergötland')),
    ('F', _(u'Jönköping')),
    ('G', _(u'Kronoberg')),
    ('H', _(u'Kalmar')),
    ('I', _(u'Gotland')),
    ('K', _(u'Blekinge')),
    ('M', _(u'Skåne')),
    ('N', _(u'Halland')),
    ('O', _(u'Västra Götaland')),
    ('S', _(u'Värmland')),
    ('T', _(u'Örebro')),
    ('U', _(u'Västmanland')),
    ('W', _(u'Dalarna')),
    ('X', _(u'Gävleborg')),
    ('Y', _(u'Västernorrland')),
    ('Z', _(u'Jämtland')),
)
