# -*- coding: utf-8 -*-
"""
A list of Argentinean provinces and autonomous cities as `choices` in a
formfield. From
http://www.argentina.gov.ar/argentina/portal/paginas.dhtml?pagina=425

This exists in this standalone file so that it's only imported into memory
when explicitly needed.
"""
from __future__ import unicode_literals

PROVINCE_CHOICES = (
    ('B', 'Buenos Aires'),
    ('K', 'Catamarca'),
    ('H', 'Chaco'),
    ('U', 'Chubut'),
    ('C', 'Ciudad Autónoma de Buenos Aires'),
    ('X', 'Córdoba'),
    ('W', 'Corrientes'),
    ('E', 'Entre Ríos'),
    ('P', 'Formosa'),
    ('Y', 'Jujuy'),
    ('L', 'La Pampa'),
    ('F', 'La Rioja'),
    ('M', 'Mendoza'),
    ('N', 'Misiones'),
    ('Q', 'Neuquén'),
    ('R', 'Río Negro'),
    ('A', 'Salta'),
    ('J', 'San Juan'),
    ('D', 'San Luis'),
    ('Z', 'Santa Cruz'),
    ('S', 'Santa Fe'),
    ('G', 'Santiago del Estero'),
    ('V', 'Tierra del Fuego, Antártida e Islas del Atlántico Sur'),
    ('T', 'Tucumán'),
)
