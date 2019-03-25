# -*- coding: utf-8 -*-
# Author: David Goodger
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 4229 $
# Date: $Date: 2005-12-23 00:46:16 +0100 (Fri, 23 Dec 2005) $
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Galician-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'atenci\u00f3n': 'attention',
      'advertencia': 'caution',
      'code (translation required)': 'code',
      'perigo': 'danger',
      'erro': 'error',
      'pista': 'hint',
      'importante': 'important',
      'nota': 'note',
      'consello': 'tip',
      'aviso': 'warning',
      'admonici\u00f3n': 'admonition',
      'barra lateral': 'sidebar',
      't\u00f3pico': 'topic',
      'bloque-li\u00f1a': 'line-block',
      'literal-analizado': 'parsed-literal',
      'r\u00fabrica': 'rubric',
      'ep\u00edgrafe': 'epigraph',
      'realzados': 'highlights',
      'coller-citaci\u00f3n': 'pull-quote',
      'compor': 'compound',
      'recipiente': 'container',
      #'questions': 'questions',
      't\u00e1boa': 'table',
      't\u00e1boa-csv': 'csv-table',
      't\u00e1boa-listaxe': 'list-table',
      #'qa': 'questions',
      #'faq': 'questions',
      'meta': 'meta',
      'math (translation required)': 'math',
      #'imagemap': 'imagemap',
      'imaxe': 'image',
      'figura': 'figure',
      'inclu\u00edr': 'include',
      'cru': 'raw',
      'substitu\u00edr': 'replace',
      'unicode': 'unicode',
      'data': 'date',
      'clase': 'class',
      'regra': 'role',
      'regra-predeterminada': 'default-role',
      't\u00edtulo': 'title',
      'contido': 'contents',
      'seccnum': 'sectnum',
      'secci\u00f3n-numerar': 'sectnum',
      'cabeceira': 'header',
      'p\u00e9 de p\u00e1xina': 'footer',
      #'footnotes': 'footnotes',
      #'citations': 'citations',
      'notas-destino': 'target-notes',
      'texto restruturado-proba-directiva': 'restructuredtext-test-directive'}
"""Galician name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'abreviatura': 'abbreviation',
    'ab': 'abbreviation',
    'acr\u00f3nimo': 'acronym',
    'ac': 'acronym',
    'code (translation required)': 'code',
    '\u00edndice': 'index',
    'i': 'index',
    'sub\u00edndice': 'subscript',
    'sub': 'subscript',
    'super\u00edndice': 'superscript',
    'sup': 'superscript',
    'referencia t\u00edtulo': 'title-reference',
    't\u00edtulo': 'title-reference',
    't': 'title-reference',
    'referencia-pep': 'pep-reference',
    'pep': 'pep-reference',
    'referencia-rfc': 'rfc-reference',
    'rfc': 'rfc-reference',
    '\u00e9nfase': 'emphasis',
    'forte': 'strong',
    'literal': 'literal',
    'math (translation required)': 'math',
    'referencia-nome': 'named-reference',
    'referencia-an\u00f3nimo': 'anonymous-reference',
    'referencia-nota ao p\u00e9': 'footnote-reference',
    'referencia-citaci\u00f3n': 'citation-reference',
    'referencia-substituci\u00f3n': 'substitution-reference',
    'destino': 'target',
    'referencia-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'cru': 'raw',}
"""Mapping of Galician role names to canonical role names for interpreted text.
"""
