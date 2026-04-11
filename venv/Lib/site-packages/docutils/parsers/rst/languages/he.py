# Author: Meir Kriheli
# Id: $Id: he.py 9452 2023-09-27 00:11:54Z milde $
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
    'תשומת לב': 'attention',
    'זהירות': 'caution',
    'code (translation required)': 'code',
    'סכנה': 'danger',
    'שגיאה': 'error',
    'רמז': 'hint',
    'חשוב': 'important',
    'הערה': 'note',
    'טיפ': 'tip',
    'אזהרה': 'warning',
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
    'table': 'table',
    'csv-table': 'csv-table',
    'list-table': 'list-table',
    'meta': 'meta',
    'math (translation required)': 'math',
    'תמונה': 'image',
    'figure': 'figure',
    'include': 'include',
    'raw': 'raw',
    'replace': 'replace',
    'unicode': 'unicode',
    'date': 'date',
    'סגנון': 'class',
    'role': 'role',
    'default-role': 'default-role',
    'title': 'title',
    'תוכן': 'contents',
    'sectnum': 'sectnum',
    'section-numbering': 'sectnum',
    'header': 'header',
    'footer': 'footer',
    'target-notes': 'target-notes',
    'restructuredtext-test-directive': 'restructuredtext-test-directive',
    # 'questions': 'questions',
    # 'qa': 'questions',
    # 'faq': 'questions',
    # 'imagemap': 'imagemap',
    # 'footnotes': 'footnotes',
    # 'citations': 'citations',
    }
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
    'תחתי': 'subscript',
    'sub': 'subscript',
    'עילי': 'superscript',
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
