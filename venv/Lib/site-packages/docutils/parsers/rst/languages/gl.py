# Author: David Goodger
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 4229 $
# Date: $Date: 2005-12-23 00:46:16 +0100 (Fri, 23 Dec 2005) $
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Galician-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'admonition (translation required)': 'admonition',
      'atención': 'attention',
      'advertencia': 'caution',
      'code (translation required)': 'code',
      'perigo': 'danger',
      'erro': 'error',
      'pista': 'hint',
      'importante': 'important',
      'nota': 'note',
      'consello': 'tip',
      'aviso': 'warning',
      'barra lateral': 'sidebar',
      'tópico': 'topic',
      'bloque-liña': 'line-block',
      'literal-analizado': 'parsed-literal',
      'rúbrica': 'rubric',
      'epígrafe': 'epigraph',
      'realzados': 'highlights',
      'coller-citación': 'pull-quote',
      'compor': 'compound',
      'recipiente': 'container',
      'táboa': 'table',
      'táboa-csv': 'csv-table',
      'táboa-listaxe': 'list-table',
      'meta': 'meta',
      'math (translation required)': 'math',
      'imaxe': 'image',
      'figura': 'figure',
      'incluír': 'include',
      'cru': 'raw',
      'substituír': 'replace',
      'unicode': 'unicode',
      'data': 'date',
      'clase': 'class',
      'regra': 'role',
      'regra-predeterminada': 'default-role',
      'título': 'title',
      'contido': 'contents',
      'seccnum': 'sectnum',
      'sección-numerar': 'sectnum',
      'cabeceira': 'header',
      'pé de páxina': 'footer',
      'notas-destino': 'target-notes',
      'texto restruturado-proba-directiva': 'restructuredtext-test-directive',
      }
"""Galician name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'abreviatura': 'abbreviation',
    'ab': 'abbreviation',
    'acrónimo': 'acronym',
    'ac': 'acronym',
    'code (translation required)': 'code',
    'índice': 'index',
    'i': 'index',
    'subíndice': 'subscript',
    'sub': 'subscript',
    'superíndice': 'superscript',
    'sup': 'superscript',
    'referencia título': 'title-reference',
    'título': 'title-reference',
    't': 'title-reference',
    'referencia-pep': 'pep-reference',
    'pep': 'pep-reference',
    'referencia-rfc': 'rfc-reference',
    'rfc': 'rfc-reference',
    'énfase': 'emphasis',
    'forte': 'strong',
    'literal': 'literal',
    'math (translation required)': 'math',
    'referencia-nome': 'named-reference',
    'referencia-anónimo': 'anonymous-reference',
    'referencia-nota ao pé': 'footnote-reference',
    'referencia-citación': 'citation-reference',
    'referencia-substitución': 'substitution-reference',
    'destino': 'target',
    'referencia-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'cru': 'raw',
    }
"""Mapping of Galician role names to canonical role names for interpreted text.
"""
