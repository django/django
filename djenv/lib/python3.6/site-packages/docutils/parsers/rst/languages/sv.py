# -*- coding: utf-8 -*-
# $Id: sv.py 8012 2017-01-03 23:08:19Z milde $
# Author: Adam Chodorowski <chodorowski@users.sourceforge.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Swedish language mappings for language-dependent features of reStructuredText.
"""

__docformat__ = 'reStructuredText'

directives = {
      'observera': 'attention',
      'akta': 'caution', # also 'försiktigt'
      'kod': 'code',
      'fara': 'danger',
      'fel': 'error',
      'vink': 'hint', # also 'hint'
      'viktigt': 'important',
      'notera': 'note',
      'tips': 'tip',
      'varning': 'warning',
      'anmärkning': 'admonition', # literal 'tillrättavisning', 'förmaning'
      'sidorad': 'sidebar',
      'ämne': 'topic',
      'tema': 'topic',
      'rad-block': 'line-block',
      'parsed-literal (translation required)': 'parsed-literal', # 'tolkad-bokstavlig'?
      'rubrik': 'rubric',
      'epigraf': 'epigraph',
      'höjdpunkter': 'highlights',
      'pull-quote (translation required)': 'pull-quote',
      'sammansatt': 'compound',
      'container': 'container',
      # u'frågor': 'questions',
      # NOTE: A bit long, but recommended by http://www.nada.kth.se/dataterm/:
      # u'frågor-och-svar': 'questions',
      # u'vanliga-frågor': 'questions',
      'tabell': 'table',
      'csv-tabell': 'csv-table',
      'list-tabell': 'list-table',
      'meta': 'meta',
      'matematik': 'math',
      # u'bildkarta': 'imagemap',   # FIXME: Translation might be too literal.
      'bild': 'image',
      'figur': 'figure',
      'inkludera': 'include',
      'rå': 'raw',
      'ersätta': 'replace',
      'unicode': 'unicode',
      'datum': 'date',
      'klass': 'class',
      'roll': 'role',
      'standardroll': 'default-role',
      'titel': 'title',
      'innehåll': 'contents',
      'sektionsnumrering': 'sectnum',
      'target-notes (translation required)': 'target-notes',
      'sidhuvud': 'header',
      'sidfot': 'footer',
      # u'fotnoter': 'footnotes',
      # u'citeringar': 'citations',
      }
"""Swedish name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
      'förkortning': 'abbreviation',
      'akronym': 'acronym',
      'kod': 'code',
      'index': 'index',
      'nedsänkt': 'subscript',
      'upphöjd': 'superscript',
      'titel-referens': 'title-reference',
      'pep-referens': 'pep-reference',
      'rfc-referens': 'rfc-reference',
      'betoning': 'emphasis',
      'stark': 'strong',
      'bokstavlig': 'literal', # also 'ordagranna'
      'matematik': 'math',
      'namngiven-referens': 'named-reference',
      'anonym-referens': 'anonymous-reference',
      'fotnot-referens': 'footnote-reference',
      'citat-referens': 'citation-reference',
      'ersättnings-referens': 'substitution-reference',
      'mål': 'target',
      'uri-referens': 'uri-reference',
      'rå': 'raw',}
"""Mapping of Swedish role names to canonical role names for interpreted text.
"""
