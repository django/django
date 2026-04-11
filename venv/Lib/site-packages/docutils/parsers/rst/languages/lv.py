# $Id: lv.py 10039 2025-03-08 18:53:20Z aa-turner $
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Latvian-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'uzmanību': 'attention',
      'piesardzību': 'caution',
      'kods': 'code',
      'koda-bloks': 'code',
      'pirmkods': 'code',
      'bīstami': 'danger',
      'kļūda': 'error',
      'ieteikums': 'hint',
      'svarīgi': 'important',
      'piezīme': 'note',
      'padoms': 'tip',
      'brīdinājums': 'warning',
      'aizrādījums': 'admonition',
      'sānjosla': 'sidebar',
      'tēma': 'topic',
      'rindu-bloks': 'line-block',
      'parsēts-literālis': 'parsed-literal',
      'rubrika': 'rubric',
      'epigrāfs': 'epigraph',
      'apskats': 'highlights',
      'izvilkuma-citāts': 'pull-quote',
      'savienojums': 'compound',
      'konteiners': 'container',
      # 'questions': 'questions',
      'tabula': 'table',
      'csv-tabula': 'csv-table',
      'sarakstveida-tabula': 'list-table',
      # 'qa': 'questions',
      # 'faq': 'questions',
      'meta': 'meta',
      'matemātika': 'math',
      # 'imagemap': 'imagemap',
      'attēls': 'image',
      'figūra': 'figure',
      'ietvert': 'include',
      'burtiski': 'raw',
      'aizvieto': 'replace',
      'unicode': 'unicode',
      'datums': 'date',
      'klase': 'class',
      'role': 'role',
      'noklusējuma-role': 'default-role',
      'virsraksts': 'title',
      'saturs': 'contents',
      'numurēt-sekcijas': 'sectnum',
      'galvene': 'header',
      'kājene': 'footer',
      # 'footnotes': 'footnotes',
      # 'citations': 'citations',
      'atsauces-apakšā': 'target-notes',
      'restructuredtext-testa-direktīva': 'restructuredtext-test-directive'}
"""English name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'saīsinājums': 'abbreviation',
    'īsi': 'abbreviation',
    'akronīms': 'acronym',
    'kods': 'code',
    'indekss': 'index',
    'i': 'index',
    'apakšraksts': 'subscript',
    'apakšā': 'subscript',
    'augšraksts': 'superscript',
    'augšā': 'superscript',
    'virsraksta-atsauce': 'title-reference',
    'virsraksts': 'title-reference',
    'v': 'title-reference',
    'atsauce-uz-pep': 'pep-reference',
    'pep': 'pep-reference',
    'atsauce-uz-rfc': 'rfc-reference',
    'rfc': 'rfc-reference',
    'izcēlums': 'emphasis',
    'blīvs': 'strong',
    'literālis': 'literal',
    'matemātika': 'math',
    'nosaukta-atsauce': 'named-reference',
    'nenosaukta-atsauce': 'anonymous-reference',
    'kājenes-atsauce': 'footnote-reference',
    'citātā-atsauce': 'citation-reference',
    'aizvietojuma-atsauce': 'substitution-reference',
    'mērkis': 'target',
    'atsauce-uz-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'burtiski': 'raw',
    }
"""Mapping of English role names to canonical role names for interpreted text.
"""
