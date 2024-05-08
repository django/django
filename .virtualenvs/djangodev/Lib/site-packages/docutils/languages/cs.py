# $Id: cs.py 9452 2023-09-27 00:11:54Z milde $
# Author: Marek Blaha <mb@dat.cz>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Czech-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Autor',
      'authors': 'Autoři',
      'organization': 'Organizace',
      'address': 'Adresa',
      'contact': 'Kontakt',
      'version': 'Verze',
      'revision': 'Revize',
      'status': 'Stav',
      'date': 'Datum',
      'copyright': 'Copyright',
      'dedication': 'Věnování',
      'abstract': 'Abstrakt',
      'attention': 'Pozor!',
      'caution': 'Opatrně!',
      'danger': '!NEBEZPEČÍ!',
      'error': 'Chyba',
      'hint': 'Rada',
      'important': 'Důležité',
      'note': 'Poznámka',
      'tip': 'Tip',
      'warning': 'Varování',
      'contents': 'Obsah'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autor': 'author',
      'autoři': 'authors',
      'organizace': 'organization',
      'adresa': 'address',
      'kontakt': 'contact',
      'verze': 'version',
      'revize': 'revision',
      'stav': 'status',
      'datum': 'date',
      'copyright': 'copyright',
      'věnování': 'dedication',
      'abstrakt': 'abstract'}
"""Czech (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
