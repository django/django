# $Id: en.py 9120 2022-09-13 10:24:30Z milde $
# Author: David Goodger <goodger@python.org>
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
      'attention': 'attention',
      'caution': 'caution',
      'danger': 'danger',
      'error': 'error',
      'hint': 'hint',
      'important': 'important',
      'note': 'note',
      'tip': 'tip',
      'warning': 'warning',
      'admonition': 'admonition',  # advice/caveat/remark, not reprimand
      'sidebar': 'sidebar',
      'topic': 'topic',
      'line-block': 'line-block',
      'parsed-literal': 'parsed-literal',
      'code': 'code',
      'code-block': 'code',
      'sourcecode': 'code',
      'math': 'math',
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
      # 'imagemap': 'imagemap',
      'image': 'image',
      'figure': 'figure',
      'include': 'include',
      'raw': 'raw',
      'replace': 'replace',
      'unicode': 'unicode',
      'date': 'date',
      'class': 'class',
      'role': 'role',
      'default-role': 'default-role',
      'title': 'title',
      'contents': 'contents',
      'sectnum': 'sectnum',
      'section-numbering': 'sectnum',
      'header': 'header',
      'footer': 'footer',
      # 'footnotes': 'footnotes',
      # 'citations': 'citations',
      'target-notes': 'target-notes',
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Mapping of English directive name to registered directive names

Cf. https://docutils.sourceforge.io/docs/ref/rst/directives.html
and `_directive_registry` in ``directives/__init__.py``.
"""

roles = {
    # language-dependent: fixed
    'abbreviation': 'abbreviation',
    'ab': 'abbreviation',
    'acronym': 'acronym',
    'ac': 'acronym',
    'code': 'code',
    'emphasis': 'emphasis',
    'literal': 'literal',
    'math': 'math',
    'pep-reference': 'pep-reference',
    'pep': 'pep-reference',
    'rfc-reference': 'rfc-reference',
    'rfc': 'rfc-reference',
    'strong': 'strong',
    'subscript': 'subscript',
    'sub': 'subscript',
    'superscript': 'superscript',
    'sup': 'superscript',
    'title-reference': 'title-reference',
    'title': 'title-reference',
    't': 'title-reference',
    'raw': 'raw',
    # the following roles are not implemented in Docutils
    'index': 'index',
    'i': 'index',
    'anonymous-reference': 'anonymous-reference',
    'citation-reference': 'citation-reference',
    'footnote-reference': 'footnote-reference',
    'named-reference': 'named-reference',
    'substitution-reference': 'substitution-reference',
    'uri-reference': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'target': 'target',
    }
"""Mapping of English role names to canonical role names for interpreted text.

Cf. https://docutils.sourceforge.io/docs/ref/rst/roles.html
"""
