# $Id: sk.py 9030 2022-03-05 23:28:32Z milde $
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
      'organization': 'Organiz\u00E1cia',
      'address': 'Adresa',
      'contact': 'Kontakt',
      'version': 'Verzia',
      'revision': 'Rev\u00EDzia',
      'status': 'Stav',
      'date': 'D\u00E1tum',
      'copyright': 'Copyright',
      'dedication': 'Venovanie',
      'abstract': 'Abstraktne',
      'attention': 'Pozor!',
      'caution': 'Opatrne!',
      'danger': '!NEBEZPE\u010cENSTVO!',
      'error': 'Chyba',
      'hint': 'Rada',
      'important': 'D\u00F4le\u017Eit\u00E9',
      'note': 'Pozn\u00E1mka',
      'tip': 'Tip',
      'warning': 'Varovanie',
      'contents': 'Obsah'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      'autor': 'author',
      'autori': 'authors',
      'organiz\u00E1cia': 'organization',
      'adresa': 'address',
      'kontakt': 'contact',
      'verzia': 'version',
      'rev\u00EDzia': 'revision',
      'stav': 'status',
      'd\u00E1tum': 'date',
      'copyright': 'copyright',
      'venovanie': 'dedication',
      'abstraktne': 'abstract'}
"""Slovak (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
