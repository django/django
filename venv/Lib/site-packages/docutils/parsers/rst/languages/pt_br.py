# $Id: pt_br.py 9782 2024-07-29 12:37:02Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Brazilian Portuguese-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'atenção': 'attention',
      'cuidado': 'caution',
      'code (translation required)': 'code',
      'perigo': 'danger',
      'erro': 'error',
      'sugestão': 'hint',
      'importante': 'important',
      'nota': 'note',
      'dica': 'tip',
      'aviso': 'warning',
      'advertência': 'admonition',
      'barra-lateral': 'sidebar',
      'tópico': 'topic',
      'bloco-de-linhas': 'line-block',
      'literal-interpretado': 'parsed-literal',
      'rubrica': 'rubric',
      'epígrafo': 'epigraph',
      'destaques': 'highlights',
      'citação-destacada': 'pull-quote',
      'compound (translation required)': 'compound',
      'container (translation required)': 'container',
      # 'perguntas': 'questions',
      # 'qa': 'questions',
      # 'faq': 'questions',
      'table (translation required)': 'table',
      'csv-table (translation required)': 'csv-table',
      'list-table (translation required)': 'list-table',
      'meta': 'meta',
      'math (translation required)': 'math',
      # 'imagemap': 'imagemap',
      'imagem': 'image',
      'figura': 'figure',
      'inclusão': 'include',
      'cru': 'raw',
      'substituição': 'replace',
      'unicode': 'unicode',
      'data': 'date',
      'classe': 'class',
      'role (translation required)': 'role',
      'default-role (translation required)': 'default-role',
      'title (translation required)': 'title',
      'índice': 'contents',
      'numsec': 'sectnum',
      'numeração-de-seções': 'sectnum',
      'header (translation required)': 'header',
      'footer (translation required)': 'footer',
      # 'notas-de-rorapé': 'footnotes',
      # 'citações': 'citations',
      'links-no-rodapé': 'target-notes',
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Brazilian Portuguese name to registered (in directives/__init__.py)
directive name mapping."""

roles = {
    # language-dependent: fixed
    'abbreviação': 'abbreviation',
    'ab': 'abbreviation',
    'acrônimo': 'acronym',
    'ac': 'acronym',
    'code (translation required)': 'code',
    'índice-remissivo': 'index',
    'i': 'index',
    'subscrito': 'subscript',
    'sub': 'subscript',
    'sobrescrito': 'superscript',
    'sob': 'superscript',
    'referência-a-título': 'title-reference',
    'título': 'title-reference',
    't': 'title-reference',
    'referência-a-pep': 'pep-reference',
    'pep': 'pep-reference',
    'referência-a-rfc': 'rfc-reference',
    'rfc': 'rfc-reference',
    'ênfase': 'emphasis',
    'forte': 'strong',
    'literal': 'literal',
    'math (translation required)': 'math',  # translation required?
    'referência-por-nome': 'named-reference',
    'referência-anônima': 'anonymous-reference',
    'referência-a-nota-de-rodapé': 'footnote-reference',
    'referência-a-citação': 'citation-reference',
    'referência-a-substituição': 'substitution-reference',
    'alvo': 'target',
    'referência-a-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'cru': 'raw',
    }
"""Mapping of Brazilian Portuguese role names to canonical role names
for interpreted text."""
