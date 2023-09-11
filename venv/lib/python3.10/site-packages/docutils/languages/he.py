# Author: Meir Kriheli
# Id: $Id: he.py 9030 2022-03-05 23:28:32Z milde $
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Hebrew-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': '\u05de\u05d7\u05d1\u05e8',
      'authors': '\u05de\u05d7\u05d1\u05e8\u05d9',
      'organization': '\u05d0\u05e8\u05d2\u05d5\u05df',
      'address': '\u05db\u05ea\u05d5\u05d1\u05ea',
      'contact': '\u05d0\u05d9\u05e9 \u05e7\u05e9\u05e8',
      'version': '\u05d2\u05e8\u05e1\u05d4',
      'revision': '\u05de\u05d4\u05d3\u05d5\u05e8\u05d4',
      'status': '\u05e1\u05d8\u05d8\u05d5\u05e1',
      'date': '\u05ea\u05d0\u05e8\u05d9\u05da',
      'copyright': ('\u05d6\u05db\u05d5\u05d9\u05d5\u05ea '
                    '\u05e9\u05de\u05d5\u05e8\u05d5\u05ea'),
      'dedication': '\u05d4\u05e7\u05d3\u05e9\u05d4',
      'abstract': '\u05ea\u05e7\u05e6\u05d9\u05e8',
      'attention': '\u05ea\u05e9\u05d5\u05de\u05ea \u05dc\u05d1',
      'caution': '\u05d6\u05d4\u05d9\u05e8\u05d5\u05ea',
      'danger': '\u05e1\u05db\u05e0\u05d4',
      'error': '\u05e9\u05d2\u05d9\u05d0\u05d4',
      'hint': '\u05e8\u05de\u05d6',
      'important': '\u05d7\u05e9\u05d5\u05d1',
      'note': '\u05d4\u05e2\u05e8\u05d4',
      'tip': '\u05d8\u05d9\u05e4',
      'warning': '\u05d0\u05d6\u05d4\u05e8\u05d4',
      'contents': '\u05ea\u05d5\u05db\u05df'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      '\u05de\u05d7\u05d1\u05e8': 'author',
      '\u05de\u05d7\u05d1\u05e8\u05d9': 'authors',
      '\u05d0\u05e8\u05d2\u05d5\u05df': 'organization',
      '\u05db\u05ea\u05d5\u05d1\u05ea': 'address',
      '\u05d0\u05d9\u05e9 \u05e7\u05e9\u05e8': 'contact',
      '\u05d2\u05e8\u05e1\u05d4': 'version',
      '\u05de\u05d4\u05d3\u05d5\u05e8\u05d4': 'revision',
      '\u05e1\u05d8\u05d8\u05d5\u05e1': 'status',
      '\u05ea\u05d0\u05e8\u05d9\u05da': 'date',
      '\u05d6\u05db\u05d5\u05d9\u05d5\u05ea \u05e9\u05de\u05d5\u05e8\u05d5\u05ea': 'copyright',  # noqa:E501
      '\u05d4\u05e7\u05d3\u05e9\u05d4': 'dedication',
      '\u05ea\u05e7\u05e6\u05d9\u05e8': 'abstract'}
"""Hebrew to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
