# $Id: sk.py 9452 2023-09-27 00:11:54Z milde $
# Author: Miroslav Vasko <zemiak@zoznam.sk>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Slovak-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      'author': 'Autor',
      'authors': 'Autori',
      'organization': 'Organizácia',
      'address': 'Adresa',
      'contact': 'Kontakt',
      'version': 'Verzia',
      'revision': 'Revízia',
      'status': 'Stav',
      'date': 'Dátum',
      'copyright': 'Copyright',
      'dedication': 'Venovanie',
      'abstract': 'Abstraktne',
      'attention': 'Pozor!',
      'caution': 'Opatrne!',
      'danger': '!NEBEZPEČENSTVO!',
      'error': 'Chyba',
      'hint': 'Rada',
      'important': 'Dôležité',
      'note': 'Poznámka',
      'tip': 'Tip',
      'warning': 'Varovanie',
      'contents': 'Obsah'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      'autor': 'author',
      'autori': 'authors',
      'organizácia': 'organization',
      'adresa': 'address',
      'kontakt': 'contact',
      'verzia': 'version',
      'revízia': 'revision',
      'stav': 'status',
      'dátum': 'date',
      'copyright': 'copyright',
      'venovanie': 'dedication',
      'abstraktne': 'abstract'}
"""Slovak (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
