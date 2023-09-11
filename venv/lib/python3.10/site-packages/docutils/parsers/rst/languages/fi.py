# $Id: fi.py 9030 2022-03-05 23:28:32Z milde $
# Author: Asko Soukka <asko.soukka@iki.fi>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Finnish-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'huomio': 'attention',
      'varo': 'caution',
      'code (translation required)': 'code',
      'vaara': 'danger',
      'virhe': 'error',
      'vihje': 'hint',
      't\u00e4rke\u00e4\u00e4': 'important',
      'huomautus': 'note',
      'neuvo': 'tip',
      'varoitus': 'warning',
      'kehotus': 'admonition',
      'sivupalkki': 'sidebar',
      'aihe': 'topic',
      'rivi': 'line-block',
      'tasalevyinen': 'parsed-literal',
      'ohje': 'rubric',
      'epigraafi': 'epigraph',
      'kohokohdat': 'highlights',
      'lainaus': 'pull-quote',
      'taulukko': 'table',
      'csv-taulukko': 'csv-table',
      'list-table (translation required)': 'list-table',
      'compound (translation required)': 'compound',
      'container (translation required)': 'container',
      # 'kysymykset': 'questions',
      'meta': 'meta',
      'math (translation required)': 'math',
      # 'kuvakartta': 'imagemap',
      'kuva': 'image',
      'kaavio': 'figure',
      'sis\u00e4llyt\u00e4': 'include',
      'raaka': 'raw',
      'korvaa': 'replace',
      'unicode': 'unicode',
      'p\u00e4iv\u00e4ys': 'date',
      'luokka': 'class',
      'rooli': 'role',
      'default-role (translation required)': 'default-role',
      'title (translation required)': 'title',
      'sis\u00e4llys': 'contents',
      'kappale': 'sectnum',
      'header (translation required)': 'header',
      'footer (translation required)': 'footer',
      # 'alaviitteet': 'footnotes',
      # 'viitaukset': 'citations',
      'target-notes (translation required)': 'target-notes'}
"""Finnish name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'lyhennys': 'abbreviation',
    'akronyymi': 'acronym',
    'kirjainsana': 'acronym',
    'code (translation required)': 'code',
    'hakemisto': 'index',
    'luettelo': 'index',
    'alaindeksi': 'subscript',
    'indeksi': 'subscript',
    'yl\u00e4indeksi': 'superscript',
    'title-reference (translation required)': 'title-reference',
    'title (translation required)': 'title-reference',
    'pep-reference (translation required)': 'pep-reference',
    'rfc-reference (translation required)': 'rfc-reference',
    'korostus': 'emphasis',
    'vahvistus': 'strong',
    'tasalevyinen': 'literal',
    'math (translation required)': 'math',
    'named-reference (translation required)': 'named-reference',
    'anonymous-reference (translation required)': 'anonymous-reference',
    'footnote-reference (translation required)': 'footnote-reference',
    'citation-reference (translation required)': 'citation-reference',
    'substitution-reference (translation required)': 'substitution-reference',
    'kohde': 'target',
    'uri-reference (translation required)': 'uri-reference',
    'raw (translation required)': 'raw',
    }
"""Mapping of Finnish role names to canonical role names for interpreted text.
"""
