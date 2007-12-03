# -*- coding: utf-8 -*-
"""
A list of Mexican states for use as `choices` in a formfield.

This exists in this standalone file so that it's only imported into memory
when explicitly needed.
"""

from django.utils.translation import ugettext_lazy as _

STATE_CHOICES = (
    ('AGU', _(u'Aguascalientes')),
    ('BCN', _(u'Baja California')),
    ('BCS', _(u'Baja California Sur')),
    ('CAM', _(u'Campeche')),
    ('CHH', _(u'Chihuahua')),
    ('CHP', _(u'Chiapas')),
    ('COA', _(u'Coahuila')),
    ('COL', _(u'Colima')),
    ('DIF', _(u'Distrito Federal')),
    ('DUR', _(u'Durango')),
    ('GRO', _(u'Guerrero')),
    ('GUA', _(u'Guanajuato')),
    ('HID', _(u'Hidalgo')),
    ('JAL', _(u'Jalisco')),
    ('MEX', _(u'Estado de México')),
    ('MIC', _(u'Michoacán')),
    ('MOR', _(u'Morelos')),
    ('NAY', _(u'Nayarit')),
    ('NLE', _(u'Nuevo León')),
    ('OAX', _(u'Oaxaca')),
    ('PUE', _(u'Puebla')),
    ('QUE', _(u'Querétaro')),
    ('ROO', _(u'Quintana Roo')),
    ('SIN', _(u'Sinaloa')),
    ('SLP', _(u'San Luis Potosí')),
    ('SON', _(u'Sonora')),
    ('TAB', _(u'Tabasco')),
    ('TAM', _(u'Tamaulipas')),
    ('TLA', _(u'Tlaxcala')),
    ('VER', _(u'Veracruz')),
    ('YUC', _(u'Yucatán')),
    ('ZAC', _(u'Zacatecas')),
)

