# $Id: eo.py 9030 2022-03-05 23:28:32Z milde $
# Author: Marcelo Huerta San Martin <richieadler@users.sourceforge.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Esperanto-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'A\u016dtoro',
      'authors': 'A\u016dtoroj',
      'organization': 'Organizo',
      'address': 'Adreso',
      'contact': 'Kontakto',
      'version': 'Versio',
      'revision': 'Revido',
      'status': 'Stato',
      'date': 'Dato',
      # 'copyright': 'Kopirajto',
      'copyright': 'A\u016dtorrajto',
      'dedication': 'Dedi\u0109o',
      'abstract': 'Resumo',
      'attention': 'Atentu!',
      'caution': 'Zorgu!',
      'danger': 'DAN\u011cERO!',
      'error': 'Eraro',
      'hint': 'Spuro',
      'important': 'Grava',
      'note': 'Noto',
      'tip': 'Helpeto',
      'warning': 'Averto',
      'contents': 'Enhavo'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'a\u016dtoro': 'author',
      'a\u016dtoroj': 'authors',
      'organizo': 'organization',
      'adreso': 'address',
      'kontakto': 'contact',
      'versio': 'version',
      'revido': 'revision',
      'stato': 'status',
      'dato': 'date',
      'a\u016dtorrajto': 'copyright',
      'dedi\u0109o': 'dedication',
      'resumo': 'abstract'}
"""Esperanto (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
