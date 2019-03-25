# -*- coding: utf-8 -*-
# $Id: da.py 7678 2013-07-03 09:57:36Z milde $
# Author: E D
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Danish-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'giv agt': 'attention',
      'pas på': 'caution',
      'kode': 'code',
      'kode-blok': 'code',
      'kildekode': 'code',
      'fare': 'danger',
      'fejl': 'error',
      'vink': 'hint',
      'vigtigt': 'important',
      'bemærk': 'note',
      'tips': 'tip',
      'advarsel': 'warning',
      'formaning': 'admonition',
      'sidebjælke': 'sidebar',
      'emne': 'topic',
      'linje-blok': 'line-block',
      'linie-blok': 'line-block',
      'parset-literal': 'parsed-literal',
      'rubrik': 'rubric',
      'epigraf': 'epigraph',
      'fremhævninger': 'highlights',
      'pull-quote (translation required)': 'pull-quote',
      'compound (translation required)': 'compound',
      'container (translation required)': 'container',
      #'questions': 'questions',
      'tabel': 'table',
      'csv-tabel': 'csv-table',
      'liste-tabel': 'list-table',
      #'qa': 'questions',
      #'faq': 'questions',
      'meta': 'meta',
      'math (translation required)': 'math',
      #'imagemap': 'imagemap',
      'billede': 'image',
      'figur': 'figure',
      'inkludér': 'include',
      'inkluder': 'include',
      'rå': 'raw',
      'erstat': 'replace',
      'unicode': 'unicode',
      'dato': 'date',
      'klasse': 'class',
      'rolle': 'role',
      'forvalgt-rolle': 'default-role',
      'titel': 'title',
      'indhold': 'contents',
      'sektnum': 'sectnum',
      'sektions-nummerering': 'sectnum',
      'sidehovede': 'header',
      'sidefod': 'footer',
      #'footnotes': 'footnotes',
      #'citations': 'citations',
      'target-notes (translation required)': 'target-notes',
      'restructuredtext-test-direktiv': 'restructuredtext-test-directive'}
"""Danish name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'forkortelse': 'abbreviation',
    'fork': 'abbreviation',
    'akronym': 'acronym',
    'ac (translation required)': 'acronym',
    'kode': 'code',
    'indeks': 'index',
    'i': 'index',
    'subscript (translation required)': 'subscript',
    'sub (translation required)': 'subscript',
    'superscript (translation required)': 'superscript',
    'sup (translation required)': 'superscript',
    'titel-reference': 'title-reference',
    'titel': 'title-reference',
    't': 'title-reference',
    'pep-reference': 'pep-reference',
    'pep': 'pep-reference',
    'rfc-reference': 'rfc-reference',
    'rfc': 'rfc-reference',
    'emfase': 'emphasis',
    'kraftig': 'strong',
    'literal': 'literal',
    'math (translation required)': 'math',
    'navngivet-reference': 'named-reference',
    'anonym-reference': 'anonymous-reference',
    'fodnote-reference': 'footnote-reference',
    'citation-reference (translation required)': 'citation-reference',
    'substitutions-reference': 'substitution-reference',
    'target (translation required)': 'target',
    'uri-reference': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'rå': 'raw',}
"""Mapping of Danish role names to canonical role names for interpreted text.
"""
