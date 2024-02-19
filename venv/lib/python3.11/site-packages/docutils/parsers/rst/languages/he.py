# Author: Meir Kriheli
# Id: $Id: he.py 9030 2022-03-05 23:28:32Z milde $
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
English-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      '\u05ea\u05e9\u05d5\u05de\u05ea \u05dc\u05d1': 'attention',
      '\u05d6\u05d4\u05d9\u05e8\u05d5\u05ea': 'caution',
      'code (translation required)': 'code',
      '\u05e1\u05db\u05e0\u05d4': 'danger',
      '\u05e9\u05d2\u05d9\u05d0\u05d4': 'error',
      '\u05e8\u05de\u05d6': 'hint',
      '\u05d7\u05e9\u05d5\u05d1': 'important',
      '\u05d4\u05e2\u05e8\u05d4': 'note',
      '\u05d8\u05d9\u05e4': 'tip',
      '\u05d0\u05d6\u05d4\u05e8\u05d4': 'warning',
      'admonition': 'admonition',
      'sidebar': 'sidebar',
      'topic': 'topic',
      'line-block': 'line-block',
      'parsed-literal': 'parsed-literal',
      'rubric': 'rubric',
      'epigraph': 'epigraph',
      'highlights': 'highlights',
      'pull-quote': 'pull-quote',
      'compound': 'compound',
      'container': 'container',
      # 'questions': 'questions',
      'table': 'table',
      'csv-table': 'csv-table',
      'list-table': 'list-table',
      # 'qa': 'questions',
      # 'faq': 'questions',
      'meta': 'meta',
      'math (translation required)': 'math',
      # 'imagemap': 'imagemap',
      '\u05ea\u05de\u05d5\u05e0\u05d4': 'image',
      'figure': 'figure',
      'include': 'include',
      'raw': 'raw',
      'replace': 'replace',
      'unicode': 'unicode',
      'date': 'date',
      '\u05e1\u05d2\u05e0\u05d5\u05df': 'class',
      'role': 'role',
      'default-role': 'default-role',
      'title': 'title',
      '\u05ea\u05d5\u05db\u05df': 'contents',
      'sectnum': 'sectnum',
      'section-numbering': 'sectnum',
      'header': 'header',
      'footer': 'footer',
      # 'footnotes': 'footnotes',
      # 'citations': 'citations',
      'target-notes': 'target-notes',
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""English name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'abbreviation': 'abbreviation',
    'ab': 'abbreviation',
    'acronym': 'acronym',
    'ac': 'acronym',
    'code (translation required)': 'code',
    'index': 'index',
    'i': 'index',
    '\u05ea\u05d7\u05ea\u05d9': 'subscript',
    'sub': 'subscript',
    '\u05e2\u05d9\u05dc\u05d9': 'superscript',
    'sup': 'superscript',
    'title-reference': 'title-reference',
    'title': 'title-reference',
    't': 'title-reference',
    'pep-reference': 'pep-reference',
    'pep': 'pep-reference',
    'rfc-reference': 'rfc-reference',
    'rfc': 'rfc-reference',
    'emphasis': 'emphasis',
    'strong': 'strong',
    'literal': 'literal',
    'math (translation required)': 'math',
    'named-reference': 'named-reference',
    'anonymous-reference': 'anonymous-reference',
    'footnote-reference': 'footnote-reference',
    'citation-reference': 'citation-reference',
    'substitution-reference': 'substitution-reference',
    'target': 'target',
    'uri-reference': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'raw': 'raw',
    }
"""Mapping of English role names to canonical role names for interpreted text.
"""
