"""
Czech regions, translations get from http://www.crwflags.com/fotw/Flags/cz-re.html
"""

from django.utils.translation import ugettext_lazy as _

REGION_CHOICES = (
    ('PR', _('Prague')),
    ('CE', _('Central Bohemian Region')),
    ('SO', _('South Bohemian Region')),
    ('PI', _('Pilsen Region')),
    ('CA', _('Carlsbad Region')),
    ('US', _('Usti Region')),
    ('LB', _('Liberec Region')),
    ('HK', _('Hradec Region')),
    ('PA', _('Pardubice Region')),
    ('VY', _('Vysocina Region')),
    ('SM', _('South Moravian Region')),
    ('OL', _('Olomouc Region')),
    ('ZL', _('Zlin Region')),
    ('MS', _('Moravian-Silesian Region')),
)
