# $Id: pt_br.py 7119 2011-09-02 13:00:23Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Brazilian Portuguese-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'aten\u00E7\u00E3o': 'attention',
      'cuidado': 'caution',
      'code (translation required)': 'code',
      'perigo': 'danger',
      'erro': 'error',
      'sugest\u00E3o': 'hint',
      'importante': 'important',
      'nota': 'note',
      'dica': 'tip',
      'aviso': 'warning',
      'exorta\u00E7\u00E3o': 'admonition',
      'barra-lateral': 'sidebar',
      't\u00F3pico': 'topic',
      'bloco-de-linhas': 'line-block',
      'literal-interpretado': 'parsed-literal',
      'rubrica': 'rubric',
      'ep\u00EDgrafo': 'epigraph',
      'destaques': 'highlights',
      'cita\u00E7\u00E3o-destacada': 'pull-quote',
      'compound (translation required)': 'compound',
      'container (translation required)': 'container',
      #'perguntas': 'questions',
      #'qa': 'questions',
      #'faq': 'questions',
      'table (translation required)': 'table',
      'csv-table (translation required)': 'csv-table',
      'list-table (translation required)': 'list-table',
      'meta': 'meta',
      'math (translation required)': 'math',
      #'imagemap': 'imagemap',
      'imagem': 'image',
      'figura': 'figure',
      'inclus\u00E3o': 'include',
      'cru': 'raw',
      'substitui\u00E7\u00E3o': 'replace',
      'unicode': 'unicode',
      'data': 'date',
      'classe': 'class',
      'role (translation required)': 'role',
      'default-role (translation required)': 'default-role',
      'title (translation required)': 'title',
      '\u00EDndice': 'contents',
      'numsec': 'sectnum',
      'numera\u00E7\u00E3o-de-se\u00E7\u00F5es': 'sectnum',
      'header (translation required)': 'header',
      'footer (translation required)': 'footer',
      #u'notas-de-rorap\u00E9': 'footnotes',
      #u'cita\u00E7\u00F5es': 'citations',
      'links-no-rodap\u00E9': 'target-notes',
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Brazilian Portuguese name to registered (in directives/__init__.py)
directive name mapping."""

roles = {
    # language-dependent: fixed
    'abbrevia\u00E7\u00E3o': 'abbreviation',
    'ab': 'abbreviation',
    'acr\u00F4nimo': 'acronym',
    'ac': 'acronym',
    'code (translation required)': 'code',
    '\u00EDndice-remissivo': 'index',
    'i': 'index',
    'subscrito': 'subscript',
    'sub': 'subscript',
    'sobrescrito': 'superscript',
    'sob': 'superscript',
    'refer\u00EAncia-a-t\u00EDtulo': 'title-reference',
    't\u00EDtulo': 'title-reference',
    't': 'title-reference',
    'refer\u00EAncia-a-pep': 'pep-reference',
    'pep': 'pep-reference',
    'refer\u00EAncia-a-rfc': 'rfc-reference',
    'rfc': 'rfc-reference',
    '\u00EAnfase': 'emphasis',
    'forte': 'strong',
    'literal': 'literal',
    'math (translation required)': 'math',               # translation required?
    'refer\u00EAncia-por-nome': 'named-reference',
    'refer\u00EAncia-an\u00F4nima': 'anonymous-reference',
    'refer\u00EAncia-a-nota-de-rodap\u00E9': 'footnote-reference',
    'refer\u00EAncia-a-cita\u00E7\u00E3o': 'citation-reference',
    'refer\u00EAncia-a-substitui\u00E7\u00E3o': 'substitution-reference',
    'alvo': 'target',
    'refer\u00EAncia-a-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'cru': 'raw',}
"""Mapping of Brazilian Portuguese role names to canonical role names
for interpreted text."""
