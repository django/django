# -*- coding: utf-8 -*-
"""
Sources:
    Croatian Counties: http://en.wikipedia.org/wiki/ISO_3166-2:HR

    Croatia doesn't have official abbreviations for counties.
    The ones provided are in common use.
"""
from django.utils.translation import ugettext_lazy as _

HR_COUNTY_CHOICES = (
    ('GZG', _('Grad Zagreb')),
    (u'BBŽ', _(u'Bjelovarsko-bilogorska županija')),
    (u'BPŽ', _(u'Brodsko-posavska županija')),
    (u'DNŽ', _(u'Dubrovačko-neretvanska županija')),
    (u'IŽ', _(u'Istarska županija')),
    (u'KŽ', _(u'Karlovačka županija')),
    (u'KKŽ', _(u'Koprivničko-križevačka županija')),
    (u'KZŽ', _(u'Krapinsko-zagorska županija')),
    (u'LSŽ', _(u'Ličko-senjska županija')),
    (u'MŽ', _(u'Međimurska županija')),
    (u'OBŽ', _(u'Osječko-baranjska županija')),
    (u'PSŽ', _(u'Požeško-slavonska županija')),
    (u'PGŽ', _(u'Primorsko-goranska županija')),
    (u'SMŽ', _(u'Sisačko-moslavačka županija')),
    (u'SDŽ', _(u'Splitsko-dalmatinska županija')),
    (u'ŠKŽ', _(u'Šibensko-kninska županija')),
    (u'VŽ', _(u'Varaždinska županija')),
    (u'VPŽ', _(u'Virovitičko-podravska županija')),
    (u'VSŽ', _(u'Vukovarsko-srijemska županija')),
    (u'ZDŽ', _(u'Zadarska županija')),
    (u'ZGŽ', _(u'Zagrebačka županija')),
)

"""
Sources:
http://hr.wikipedia.org/wiki/Dodatak:Popis_registracijskih_oznaka_za_cestovna_vozila_u_Hrvatskoj

Only common license plate prefixes are provided. Special cases and obsolete prefixes are omitted.
"""

HR_LICENSE_PLATE_PREFIX_CHOICES = (
    ('BJ', 'BJ'),
    ('BM', 'BM'),
    (u'ČK', u'ČK'),
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
    (u'KŽ', u'KŽ'),
    ('MA', 'MA'),
    ('NA', 'NA'),
    ('NG', 'NG'),
    ('OG', 'OG'),
    ('OS', 'OS'),
    ('PU', 'PU'),
    (u'PŽ', u'PŽ'),
    ('RI', 'RI'),
    ('SB', 'SB'),
    ('SK', 'SK'),
    ('SL', 'SL'),
    ('ST', 'ST'),
    (u'ŠI', u'ŠI'),
    ('VK', 'VK'),
    ('VT', 'VT'),
    ('VU', 'VU'),
    (u'VŽ', u'VŽ'),
    ('ZD', 'ZD'),
    ('ZG', 'ZG'),
    (u'ŽU', u'ŽU'),
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
