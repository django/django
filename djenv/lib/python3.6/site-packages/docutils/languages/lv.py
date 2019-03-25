# -*- coding: utf-8 -*-
# $Id: lv.py 7975 2016-10-20 20:00:19Z milde $
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Latvian-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Autors',
      'authors': 'Autori',
      'organization': 'Organizācija',
      'address': 'Adrese',
      'contact': 'Kontakti',
      'version': 'Versija',
      'revision': 'Revīzija',
      'status': 'Statuss',
      'date': 'Datums',
      'copyright': 'Copyright',
      'dedication': 'Veltījums',
      'abstract': 'Atreferējums',
      'attention': 'Uzmanību!',
      'caution': 'Piesardzību!',
      'danger': '!BĪSTAMI!',
      'error': 'Kļūda',
      'hint': 'Ieteikums',
      'important': 'Svarīgi',
      'note': 'Piezīme',
      'tip': 'Padoms',
      'warning': 'Brīdinājums',
      'contents': 'Saturs'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autors': 'author',
      'autori': 'authors',
      'organizācija': 'organization',
      'adrese': 'address',
      'kontakti': 'contact',
      'versija': 'version',
      'revīzija': 'revision',
      'statuss': 'status',
      'datums': 'date',
      'copyright': 'copyright',
      'veltījums': 'dedication',
      'atreferējums': 'abstract'}
"""English (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
