# $Id: cs.py 9030 2022-03-05 23:28:32Z milde $
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
      'authors': 'Auto\u0159i',
      'organization': 'Organizace',
      'address': 'Adresa',
      'contact': 'Kontakt',
      'version': 'Verze',
      'revision': 'Revize',
      'status': 'Stav',
      'date': 'Datum',
      'copyright': 'Copyright',
      'dedication': 'V\u011Bnov\u00E1n\u00ED',
      'abstract': 'Abstrakt',
      'attention': 'Pozor!',
      'caution': 'Opatrn\u011B!',
      'danger': '!NEBEZPE\u010C\u00CD!',
      'error': 'Chyba',
      'hint': 'Rada',
      'important': 'D\u016Fle\u017Eit\u00E9',
      'note': 'Pozn\u00E1mka',
      'tip': 'Tip',
      'warning': 'Varov\u00E1n\u00ED',
      'contents': 'Obsah'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autor': 'author',
      'auto\u0159i': 'authors',
      'organizace': 'organization',
      'adresa': 'address',
      'kontakt': 'contact',
      'verze': 'version',
      'revize': 'revision',
      'stav': 'status',
      'datum': 'date',
      'copyright': 'copyright',
      'v\u011Bnov\u00E1n\u00ED': 'dedication',
      'abstrakt': 'abstract'}
"""Czech (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
