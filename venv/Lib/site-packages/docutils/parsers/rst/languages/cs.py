# $Id: cs.py 9452 2023-09-27 00:11:54Z milde $
# Author: Marek Blaha <mb@dat.cz>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Czech-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'pozor': 'attention',
      # jak rozlisit caution a warning?
      'caution (translation required)': 'caution',
      'code (translation required)': 'code',
      'nebezpečí': 'danger',
      'chyba': 'error',
      'rada': 'hint',
      'důležité': 'important',
      'poznámka': 'note',
      'tip (translation required)': 'tip',
      'varování': 'warning',
      'admonition (translation required)': 'admonition',
      'sidebar (translation required)': 'sidebar',
      'téma': 'topic',
      'line-block (translation required)': 'line-block',
      'parsed-literal (translation required)': 'parsed-literal',
      'oddíl': 'rubric',
      'moto': 'epigraph',
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
      'math (translation required)': 'math',
      'meta (translation required)': 'meta',
      # 'imagemap': 'imagemap',
      'image (translation required)': 'image',    # obrazek
      'figure (translation required)': 'figure',  # a tady?
      'include (translation required)': 'include',
      'raw (translation required)': 'raw',
      'replace (translation required)': 'replace',
      'unicode (translation required)': 'unicode',
      'datum': 'date',
      'třída': 'class',
      'role (translation required)': 'role',
      'default-role (translation required)': 'default-role',
      'title (translation required)': 'title',
      'obsah': 'contents',
      'sectnum (translation required)': 'sectnum',
      'section-numbering (translation required)': 'sectnum',
      'header (translation required)': 'header',
      'footer (translation required)': 'footer',
      # 'footnotes': 'footnotes',
      # 'citations': 'citations',
      'target-notes (translation required)': 'target-notes',
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Czech name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'abbreviation (translation required)': 'abbreviation',
    'ab (translation required)': 'abbreviation',
    'acronym (translation required)': 'acronym',
    'ac (translation required)': 'acronym',
    'code (translation required)': 'code',
    'index (translation required)': 'index',
    'i (translation required)': 'index',
    'subscript (translation required)': 'subscript',
    'sub (translation required)': 'subscript',
    'superscript (translation required)': 'superscript',
    'sup (translation required)': 'superscript',
    'title-reference (translation required)': 'title-reference',
    'title (translation required)': 'title-reference',
    't (translation required)': 'title-reference',
    'pep-reference (translation required)': 'pep-reference',
    'pep (translation required)': 'pep-reference',
    'rfc-reference (translation required)': 'rfc-reference',
    'rfc (translation required)': 'rfc-reference',
    'emphasis (translation required)': 'emphasis',
    'strong (translation required)': 'strong',
    'literal (translation required)': 'literal',
    'math (translation required)': 'math',
    'named-reference (translation required)': 'named-reference',
    'anonymous-reference (translation required)': 'anonymous-reference',
    'footnote-reference (translation required)': 'footnote-reference',
    'citation-reference (translation required)': 'citation-reference',
    'substitution-reference (translation required)': 'substitution-reference',
    'target (translation required)': 'target',
    'uri-reference (translation required)': 'uri-reference',
    'uri (translation required)': 'uri-reference',
    'url (translation required)': 'uri-reference',
    'raw (translation required)': 'raw',
    }
"""Mapping of Czech role names to canonical role names for interpreted text.
"""
