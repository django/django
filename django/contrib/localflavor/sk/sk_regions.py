"""
Slovak regions according to http://sk.wikipedia.org/wiki/Administrat%C3%ADvne_%C4%8Dlenenie_Slovenska
"""

from django.utils.translation import ugettext_lazy as _

REGION_CHOICES = (
    ('BB', _('Banska Bystrica region')),
    ('BA', _('Bratislava region')),
    ('KE', _('Kosice region')),
    ('NR', _('Nitra region')),
    ('PO', _('Presov region')),
    ('TN', _('Trencin region')),
    ('TT', _('Trnava region')),
    ('ZA', _('Zilina region')),
)
