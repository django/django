# $Id: sk.py 9452 2023-09-27 00:11:54Z milde $
# Author: Miroslav Vasko <zemiak@zoznam.sk>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Slovak-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      'pozor': 'attention',
      'opatrne': 'caution',
      'code (translation required)': 'code',
      'nebezpe\xe8enstvo': 'danger',
      'chyba': 'error',
      'rada': 'hint',
      'd\xf4le\x9eit\xe9': 'important',
      'pozn\xe1mka': 'note',
      'tip (translation required)': 'tip',
      'varovanie': 'warning',
      'admonition (translation required)': 'admonition',
      'sidebar (translation required)': 'sidebar',
      't\xe9ma': 'topic',
      'blok-riadkov': 'line-block',
      'parsed-literal': 'parsed-literal',
      'rubric (translation required)': 'rubric',
      'epigraph (translation required)': 'epigraph',
      'highlights (translation required)': 'highlights',
      'pull-quote (translation required)': 'pull-quote',
      'compound (translation required)': 'compound',
      'container (translation required)': 'container',
      # 'questions': 'questions',
      # 'qa': 'questions',
      # 'faq': 'questions',
      'table (translation required)': 'table',
      'csv-table (translation required)': 'csv-table',
      'list-table (translation required)': 'list-table',
      'meta': 'meta',
      'math (translation required)': 'math',
      # 'imagemap': 'imagemap',
      'obr\xe1zok': 'image',
      'tvar': 'figure',
      'vlo\x9ei\x9d': 'include',
      'raw (translation required)': 'raw',
      'nahradi\x9d': 'replace',
      'unicode': 'unicode',
      'dátum': 'date',
      'class (translation required)': 'class',
      'role (translation required)': 'role',
      'default-role (translation required)': 'default-role',
      'title (translation required)': 'title',
      'obsah': 'contents',
      '\xe8as\x9d': 'sectnum',
      '\xe8as\x9d-\xe8\xedslovanie': 'sectnum',
      'cie\xbeov\xe9-pozn\xe1mky': 'target-notes',
      'header (translation required)': 'header',
      'footer (translation required)': 'footer',
      # 'footnotes': 'footnotes',
      # 'citations': 'citations',
      }
"""Slovak name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
      'abbreviation (translation required)': 'abbreviation',
      'acronym (translation required)': 'acronym',
      'code (translation required)': 'code',
      'index (translation required)': 'index',
      'subscript (translation required)': 'subscript',
      'superscript (translation required)': 'superscript',
      'title-reference (translation required)': 'title-reference',
      'pep-reference (translation required)': 'pep-reference',
      'rfc-reference (translation required)': 'rfc-reference',
      'emphasis (translation required)': 'emphasis',
      'strong (translation required)': 'strong',
      'literal (translation required)': 'literal',
      'math (translation required)': 'math',
      'named-reference (translation required)': 'named-reference',
      'anonymous-reference (translation required)': 'anonymous-reference',
      'footnote-reference (translation required)': 'footnote-reference',
      'citation-reference (translation required)': 'citation-reference',
      'substitution-reference (translation required)': 'substitution-reference',  # noqa:E501
      'target (translation required)': 'target',
      'uri-reference (translation required)': 'uri-reference',
      'raw (translation required)': 'raw',
      }
"""Mapping of Slovak role names to canonical role names for interpreted text.
"""
