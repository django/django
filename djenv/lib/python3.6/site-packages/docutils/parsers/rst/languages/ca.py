# $Id: ca.py 7119 2011-09-02 13:00:23Z milde $
# Author: Ivan Vilata i Balaguer <ivan@selidor.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Catalan-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'atenci\u00F3': 'attention',
      'compte': 'caution',
      'code (translation required)': 'code',
      'perill': 'danger',
      'error': 'error',
      'suggeriment': 'hint',
      'important': 'important',
      'nota': 'note',
      'consell': 'tip',
      'av\u00EDs': 'warning',
      'advertiment': 'admonition',
      'nota-al-marge': 'sidebar',
      'nota-marge': 'sidebar',
      'tema': 'topic',
      'bloc-de-l\u00EDnies': 'line-block',
      'bloc-l\u00EDnies': 'line-block',
      'literal-analitzat': 'parsed-literal',
      'r\u00FAbrica': 'rubric',
      'ep\u00EDgraf': 'epigraph',
      'sumari': 'highlights',
      'cita-destacada': 'pull-quote',
      'compost': 'compound',
      'container (translation required)': 'container',
      #'questions': 'questions',
      'taula': 'table',
      'taula-csv': 'csv-table',
      'taula-llista': 'list-table',
      #'qa': 'questions',
      #'faq': 'questions',
      'math (translation required)': 'math',
      'meta': 'meta',
      #'imagemap': 'imagemap',
      'imatge': 'image',
      'figura': 'figure',
      'inclou': 'include',
      'incloure': 'include',
      'cru': 'raw',
      'reempla\u00E7a': 'replace',
      'reempla\u00E7ar': 'replace',
      'unicode': 'unicode',
      'data': 'date',
      'classe': 'class',
      'rol': 'role',
      'default-role (translation required)': 'default-role',
      'title (translation required)': 'title',
      'contingut': 'contents',
      'numsec': 'sectnum',
      'numeraci\u00F3-de-seccions': 'sectnum',
      'numeraci\u00F3-seccions': 'sectnum',
      'cap\u00E7alera': 'header',
      'peu-de-p\u00E0gina': 'footer',
      'peu-p\u00E0gina': 'footer',
      #'footnotes': 'footnotes',
      #'citations': 'citations',
      'notes-amb-destinacions': 'target-notes',
      'notes-destinacions': 'target-notes',
      'directiva-de-prova-de-restructuredtext': 'restructuredtext-test-directive'}
"""Catalan name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'abreviatura': 'abbreviation',
    'abreviaci\u00F3': 'abbreviation',
    'abrev': 'abbreviation',
    'ab': 'abbreviation',
    'acr\u00F2nim': 'acronym',
    'ac': 'acronym',
    'code (translation required)': 'code',
    '\u00EDndex': 'index',
    'i': 'index',
    'sub\u00EDndex': 'subscript',
    'sub': 'subscript',
    'super\u00EDndex': 'superscript',
    'sup': 'superscript',
    'refer\u00E8ncia-a-t\u00EDtol': 'title-reference',
    'refer\u00E8ncia-t\u00EDtol': 'title-reference',
    't\u00EDtol': 'title-reference',
    't': 'title-reference',
    'refer\u00E8ncia-a-pep': 'pep-reference',
    'refer\u00E8ncia-pep': 'pep-reference',
    'pep': 'pep-reference',
    'refer\u00E8ncia-a-rfc': 'rfc-reference',
    'refer\u00E8ncia-rfc': 'rfc-reference',
    'rfc': 'rfc-reference',
    '\u00E8mfasi': 'emphasis',
    'destacat': 'strong',
    'literal': 'literal',
    'math (translation required)': 'math',
    'refer\u00E8ncia-amb-nom': 'named-reference',
    'refer\u00E8ncia-nom': 'named-reference',
    'refer\u00E8ncia-an\u00F2nima': 'anonymous-reference',
    'refer\u00E8ncia-a-nota-al-peu': 'footnote-reference',
    'refer\u00E8ncia-nota-al-peu': 'footnote-reference',
    'refer\u00E8ncia-a-cita': 'citation-reference',
    'refer\u00E8ncia-cita': 'citation-reference',
    'refer\u00E8ncia-a-substituci\u00F3': 'substitution-reference',
    'refer\u00E8ncia-substituci\u00F3': 'substitution-reference',
    'destinaci\u00F3': 'target',
    'refer\u00E8ncia-a-uri': 'uri-reference',
    'refer\u00E8ncia-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'cru': 'raw',}
"""Mapping of Catalan role names to canonical role names for interpreted text.
"""
