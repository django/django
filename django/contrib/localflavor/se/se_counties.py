# -*- coding: utf-8 -*-
"""
An alphabetical list of Swedish counties, sorted by codes.

http://en.wikipedia.org/wiki/Counties_of_Sweden

This exists in this standalone file so that it's only imported into memory
when explicitly needed.

"""
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

COUNTY_CHOICES = (
    ('AB', _('Stockholm')),
    ('AC', _('Västerbotten')),
    ('BD', _('Norrbotten')),
    ('C', _('Uppsala')),
    ('D', _('Södermanland')),
    ('E', _('Östergötland')),
    ('F', _('Jönköping')),
    ('G', _('Kronoberg')),
    ('H', _('Kalmar')),
    ('I', _('Gotland')),
    ('K', _('Blekinge')),
    ('M', _('Skåne')),
    ('N', _('Halland')),
    ('O', _('Västra Götaland')),
    ('S', _('Värmland')),
    ('T', _('Örebro')),
    ('U', _('Västmanland')),
    ('W', _('Dalarna')),
    ('X', _('Gävleborg')),
    ('Y', _('Västernorrland')),
    ('Z', _('Jämtland')),
)
