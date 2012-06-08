# -*- coding: utf-8 -*-
"""
A list of Chilean regions as `choices` in a formfield.

This exists in this standalone file so that it's only imported into memory
when explicitly needed.
"""
from __future__ import unicode_literals

REGION_CHOICES = (
    ('RM',  'Región Metropolitana de Santiago'),
    ('I',   'Región de Tarapacá'),
    ('II',  'Región de Antofagasta'),
    ('III', 'Región de Atacama'),
    ('IV',  'Región de Coquimbo'),
    ('V',   'Región de Valparaíso'),
    ('VI',  'Región del Libertador Bernardo O\'Higgins'),
    ('VII', 'Región del Maule'),
    ('VIII','Región del Bío Bío'),
    ('IX',  'Región de la Araucanía'),
    ('X',   'Región de los Lagos'),
    ('XI',  'Región de Aysén del General Carlos Ibáñez del Campo'),
    ('XII', 'Región de Magallanes y la Antártica Chilena'),
    ('XIV', 'Región de Los Ríos'),
    ('XV',  'Región de Arica-Parinacota'),
)
