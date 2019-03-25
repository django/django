# -*- coding: utf-8 -*-
# $Id: sv.py 8006 2016-12-22 23:02:44Z milde $
# Author: Adam Chodorowski <chodorowski@users.sourceforge.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Swedish language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
    'author':       'Författare',
    'authors':      'Författare',
    'organization': 'Organisation',
    'address':      'Adress',
    'contact':      'Kontakt',
    'version':      'Version',
    'revision':     'Revision',
    'status':       'Status',
    'date':         'Datum',
    'copyright':    'Copyright',
    'dedication':   'Dedikation',
    'abstract':     'Sammanfattning',
    'attention':    'Observera!',
    'caution':      'Akta!', # 'Varning' already used for 'warning'
    'danger':       'FARA!',
    'error':        'Fel',
    'hint':         'Vink',
    'important':    'Viktigt',
    'note':         'Notera',
    'tip':          'Tips',
    'warning':      'Varning',
    'contents':     'Innehåll' }
"""Mapping of node class name to label text."""

bibliographic_fields = {
    # 'Author' and 'Authors' identical in Swedish; assume the plural:
    'författare': 'authors',
    ' n/a':            'author',
    'organisation':    'organization',
    'adress':          'address',
    'kontakt':         'contact',
    'version':         'version',
    'revision':        'revision',
    'status':          'status',
    'datum':           'date',
    'copyright':       'copyright',
    'dedikation':      'dedication', 
    'sammanfattning':  'abstract' }
"""Swedish (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
