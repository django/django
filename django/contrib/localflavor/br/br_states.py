# -*- coding: utf-8 -*-
"""
A brazilian mapping of state misspellings/abbreviations to normalized
abbreviations, and an alphabetical list of states for use as `choices
in a formfield.

This exists in this standalone file so that it's only imported into
memory when explicitly needed.
"""

STATE_CHOICES = (
    ('AC', 'Acre'),
    ('AL', 'Alagoas'),
    ('AP', u'Amapá'),
    ('AM', 'Amazonas'),
    ('BA', 'Bahia'),
    ('CE', u'Ceará'),
    ('DF', 'Distrito Federal'),
    ('ES', u'Espírito Santo'),
    ('GO', u'Goiás'),
    ('MA', u'Maranhão'),
    ('MT', 'Mato Grosso'),
    ('MS', 'Mato Grosso do Sul'),
    ('MG', 'Minas Gerais'),
    ('PA', u'Pará'),
    ('PB', u'Paraíba'),
    ('PR', u'Paraná'),
    ('PE', 'Pernambuco'),
    ('PI', u'Piauí'),
    ('RJ', 'Rio de Janeiro'),
    ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'),
    ('RO', u'Rondônia'),
    ('RR', 'Roraima'),
    ('SC', 'Santa Catarina'),
    ('SP', u'São Paulo'),
    ('SE', 'Sergipe'),
    ('TO', 'Tocantins'),
)
