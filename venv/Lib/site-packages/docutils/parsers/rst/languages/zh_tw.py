# $Id: zh_tw.py 9030 2022-03-05 23:28:32Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Traditional Chinese language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'attention (translation required)': 'attention',
      'caution (translation required)': 'caution',
      'code (translation required)': 'code',
      'danger (translation required)': 'danger',
      'error (translation required)': 'error',
      'hint (translation required)': 'hint',
      'important (translation required)': 'important',
      'note (translation required)': 'note',
      'tip (translation required)': 'tip',
      'warning (translation required)': 'warning',
      'admonition (translation required)': 'admonition',
      'sidebar (translation required)': 'sidebar',
      'topic (translation required)': 'topic',
      'line-block (translation required)': 'line-block',
      'parsed-literal (translation required)': 'parsed-literal',
      'rubric (translation required)': 'rubric',
      'epigraph (translation required)': 'epigraph',
      'highlights (translation required)': 'highlights',
      'pull-quote (translation required)': 'pull-quote',
      'compound (translation required)': 'compound',
      'container (translation required)': 'container',
      # 'questions (translation required)': 'questions',
      'table (translation required)': 'table',
      'csv-table (translation required)': 'csv-table',
      'list-table (translation required)': 'list-table',
      # 'qa (translation required)': 'questions',
      # 'faq (translation required)': 'questions',
      'meta (translation required)': 'meta',
      'math (translation required)': 'math',
      # 'imagemap (translation required)': 'imagemap',
      'image (translation required)': 'image',
      'figure (translation required)': 'figure',
      'include (translation required)': 'include',
      'raw (translation required)': 'raw',
      'replace (translation required)': 'replace',
      'unicode (translation required)': 'unicode',
      '日期': 'date',
      'class (translation required)': 'class',
      'role (translation required)': 'role',
      'default-role (translation required)': 'default-role',
      'title (translation required)': 'title',
      'contents (translation required)': 'contents',
      'sectnum (translation required)': 'sectnum',
      'section-numbering (translation required)': 'sectnum',
      'header (translation required)': 'header',
      'footer (translation required)': 'footer',
      # 'footnotes (translation required)': 'footnotes',
      # 'citations (translation required)': 'citations',
      'target-notes (translation required)': 'target-notes',
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Traditional Chinese name to registered (in directives/__init__.py)
directive name mapping."""

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
"""Mapping of Traditional Chinese role names to canonical role names for
interpreted text."""
