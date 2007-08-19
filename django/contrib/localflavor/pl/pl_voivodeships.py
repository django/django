"""
Polish voivodeship as in http://en.wikipedia.org/wiki/Poland#Administrative_division
"""

from django.utils.translation import ugettext_lazy as _

VOIVODESHIP_CHOICES = (
    ('lower_silesia', _('Lower Silesia')),
    ('kuyavia-pomerania', _('Kuyavia-Pomerania')),
    ('lublin', _('Lublin')),
    ('lubusz', _('Lubusz')),
    ('lodz', _('Lodz')),
    ('lesser_poland', _('Lesser Poland')),
    ('masovia', _('Masovia')),
    ('opole', _('Opole')),
    ('subcarpatia', _('Subcarpatia')),
    ('podlasie', _('Podlasie')),
    ('pomerania', _('Pomerania')),
    ('silesia', _('Silesia')),
    ('swietokrzyskie', _('Swietokrzyskie')),
    ('warmia-masuria', _('Warmia-Masuria')),
    ('greater_poland', _('Greater Poland')),
    ('west_pomerania', _('West Pomerania')),
)
