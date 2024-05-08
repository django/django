# $Id$
# Author: Robert Wojciechowicz <rw@smsnet.pl>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Polish-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Autor',
      'authors': 'Autorzy',
      'organization': 'Organizacja',
      'address': 'Adres',
      'contact': 'Kontakt',
      'version': 'Wersja',
      'revision': 'Korekta',
      'status': 'Status',
      'date': 'Data',
      'copyright': 'Copyright',
      'dedication': 'Dedykacja',
      'abstract': 'Streszczenie',
      'attention': 'Uwaga!',
      'caution': 'Ostrożnie!',
      'danger': '!Niebezpieczeństwo!',
      'error': 'Błąd',
      'hint': 'Wskazówka',
      'important': 'Ważne',
      'note': 'Przypis',
      'tip': 'Rada',
      'warning': 'Ostrzeżenie',
      'contents': 'Treść'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autor': 'author',
      'autorzy': 'authors',
      'organizacja': 'organization',
      'adres': 'address',
      'kontakt': 'contact',
      'wersja': 'version',
      'korekta': 'revision',
      'status': 'status',
      'data': 'date',
      'copyright': 'copyright',
      'dedykacja': 'dedication',
      'streszczenie': 'abstract'}
"""Polish (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
