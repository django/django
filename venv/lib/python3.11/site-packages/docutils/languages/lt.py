# $Id: lt.py 9030 2022-03-05 23:28:32Z milde $
# Author: Dalius Dobravolskas <dalius.do...@gmail.com>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Lithuanian language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Autorius',
      'authors': 'Autoriai',
      'organization': 'Organizacija',
      'address': 'Adresas',
      'contact': 'Kontaktas',
      'version': 'Versija',
      'revision': 'Revizija',
      'status': 'Būsena',
      'date': 'Data',
      'copyright': 'Autoriaus teisės',
      'dedication': 'Dedikacija',
      'abstract': 'Santrauka',
      'attention': 'Dėmesio!',
      'caution': 'Atsargiai!',
      'danger': '!PAVOJINGA!',
      'error': 'Klaida',
      'hint': 'Užuomina',
      'important': 'Svarbu',
      'note': 'Pastaba',
      'tip': 'Patarimas',
      'warning': 'Įspėjimas',
      'contents': 'Turinys'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autorius': 'author',
      'autoriai': 'authors',
      'organizacija': 'organization',
      'adresas': 'address',
      'kontaktas': 'contact',
      'versija': 'version',
      'revizija': 'revision',
      'būsena': 'status',
      'data': 'date',
      'autoriaus teisės': 'copyright',
      'dedikacija': 'dedication',
      'santrauka': 'abstract'}
"""Lithuanian (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
