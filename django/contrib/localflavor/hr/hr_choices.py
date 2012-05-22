# -*- coding: utf-8 -*-
"""
Sources:
    Croatian Counties: http://en.wikipedia.org/wiki/ISO_3166-2:HR

    Croatia doesn't have official abbreviations for counties.
    The ones provided are in common use.
"""
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

HR_COUNTY_CHOICES = (
    ('GZG', _('Grad Zagreb')),
    ('BBŽ', _('Bjelovarsko-bilogorska županija')),
    ('BPŽ', _('Brodsko-posavska županija')),
    ('DNŽ', _('Dubrovačko-neretvanska županija')),
    ('IŽ', _('Istarska županija')),
    ('KŽ', _('Karlovačka županija')),
    ('KKŽ', _('Koprivničko-križevačka županija')),
    ('KZŽ', _('Krapinsko-zagorska županija')),
    ('LSŽ', _('Ličko-senjska županija')),
    ('MŽ', _('Međimurska županija')),
    ('OBŽ', _('Osječko-baranjska županija')),
    ('PSŽ', _('Požeško-slavonska županija')),
    ('PGŽ', _('Primorsko-goranska županija')),
    ('SMŽ', _('Sisačko-moslavačka županija')),
    ('SDŽ', _('Splitsko-dalmatinska županija')),
    ('ŠKŽ', _('Šibensko-kninska županija')),
    ('VŽ', _('Varaždinska županija')),
    ('VPŽ', _('Virovitičko-podravska županija')),
    ('VSŽ', _('Vukovarsko-srijemska županija')),
    ('ZDŽ', _('Zadarska županija')),
    ('ZGŽ', _('Zagrebačka županija')),
)

"""
Sources:
http://hr.wikipedia.org/wiki/Dodatak:Popis_registracijskih_oznaka_za_cestovna_vozila_u_Hrvatskoj

Only common license plate prefixes are provided. Special cases and obsolete prefixes are omitted.
"""

HR_LICENSE_PLATE_PREFIX_CHOICES = (
    ('BJ', 'BJ'),
    ('BM', 'BM'),
    ('ČK', 'ČK'),
    ('DA', 'DA'),
    ('DE', 'DE'),
    ('DJ', 'DJ'),
    ('DU', 'DU'),
    ('GS', 'GS'),
    ('IM', 'IM'),
    ('KA', 'KA'),
    ('KC', 'KC'),
    ('KR', 'KR'),
    ('KT', 'KT'),
    ('KŽ', 'KŽ'),
    ('MA', 'MA'),
    ('NA', 'NA'),
    ('NG', 'NG'),
    ('OG', 'OG'),
    ('OS', 'OS'),
    ('PU', 'PU'),
    ('PŽ', 'PŽ'),
    ('RI', 'RI'),
    ('SB', 'SB'),
    ('SK', 'SK'),
    ('SL', 'SL'),
    ('ST', 'ST'),
    ('ŠI', 'ŠI'),
    ('VK', 'VK'),
    ('VT', 'VT'),
    ('VU', 'VU'),
    ('VŽ', 'VŽ'),
    ('ZD', 'ZD'),
    ('ZG', 'ZG'),
    ('ŽU', 'ŽU'),
)

"""
The list includes county and cellular network phone number prefixes.
"""

HR_PHONE_NUMBER_PREFIX_CHOICES = (
    ('1', '01'),
    ('20', '020'),
    ('21', '021'),
    ('22', '022'),
    ('23', '023'),
    ('31', '031'),
    ('32', '032'),
    ('33', '033'),
    ('34', '034'),
    ('35', '035'),
    ('40', '040'),
    ('42', '042'),
    ('43', '043'),
    ('44', '044'),
    ('47', '047'),
    ('48', '048'),
    ('49', '049'),
    ('51', '051'),
    ('52', '052'),
    ('53', '053'),
    ('91', '091'),
    ('92', '092'),
    ('95', '095'),
    ('97', '097'),
    ('98', '098'),
    ('99', '099'),
)
