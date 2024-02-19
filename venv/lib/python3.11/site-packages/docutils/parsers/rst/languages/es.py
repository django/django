# $Id: es.py 9116 2022-07-28 17:06:51Z milde $
# Author: Marcelo Huerta San Martín <richieadler@users.sourceforge.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Spanish-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'

directives = {
      'atenci\u00f3n': 'attention',
      'atencion': 'attention',
      'precauci\u00f3n': 'caution',
      'code (translation required)': 'code',
      'precaucion': 'caution',
      'peligro': 'danger',
      'error': 'error',
      'sugerencia': 'hint',
      'importante': 'important',
      'nota': 'note',
      'consejo': 'tip',
      'advertencia': 'warning',
      'exhortacion': 'admonition',  # sic! Not used in this sense in rST.
      'exhortaci\u00f3n': 'admonition',
      'nota-al-margen': 'sidebar',
      'tema': 'topic',
      'bloque-de-lineas': 'line-block',
      'bloque-de-l\u00edneas': 'line-block',
      'literal-evaluado': 'parsed-literal',
      'firma': 'rubric',
      'ep\u00edgrafe': 'epigraph',
      'epigrafe': 'epigraph',
      'destacado': 'highlights',
      'cita-destacada': 'pull-quote',
      'combinacion': 'compound',
      'combinaci\u00f3n': 'compound',
      'contenedor': 'container',
      # 'questions': 'questions',
      # 'qa': 'questions',
      # 'faq': 'questions',
      'tabla': 'table',
      'tabla-vsc': 'csv-table',
      'tabla-csv': 'csv-table',
      'tabla-lista': 'list-table',
      'meta': 'meta',
      'math (translation required)': 'math',
      # 'imagemap': 'imagemap',
      'imagen': 'image',
      'figura': 'figure',
      'incluir': 'include',
      'sin-analisis': 'raw',
      'sin-an\u00e1lisis': 'raw',
      'reemplazar': 'replace',
      'unicode': 'unicode',
      'fecha': 'date',
      'clase': 'class',
      'rol': 'role',
      'rol-por-omision': 'default-role',
      'rol-por-omisi\u00f3n': 'default-role',
      'titulo': 'title',
      't\u00edtulo': 'title',
      'contenido': 'contents',
      'numseccion': 'sectnum',
      'numsecci\u00f3n': 'sectnum',
      'numeracion-seccion': 'sectnum',
      'numeraci\u00f3n-secci\u00f3n': 'sectnum',
      'notas-destino': 'target-notes',
      'cabecera': 'header',
      'pie': 'footer',
      # 'footnotes': 'footnotes',
      # 'citations': 'citations',
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Spanish name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    'abreviatura': 'abbreviation',
    'ab': 'abbreviation',
    'acronimo': 'acronym',
    'ac': 'acronym',
    'code (translation required)': 'code',
    'indice': 'index',
    'i': 'index',
    'subindice': 'subscript',
    'sub\u00edndice': 'subscript',
    'superindice': 'superscript',
    'super\u00edndice': 'superscript',
    'referencia-titulo': 'title-reference',
    'titulo': 'title-reference',
    't': 'title-reference',
    'referencia-pep': 'pep-reference',
    'pep': 'pep-reference',
    'referencia-rfc': 'rfc-reference',
    'rfc': 'rfc-reference',
    'enfasis': 'emphasis',
    '\u00e9nfasis': 'emphasis',
    'destacado': 'strong',
    'literal': 'literal',  # "literal" is also a word in Spanish :-)
    'math (translation required)': 'math',
    'referencia-con-nombre': 'named-reference',
    'referencia-anonima': 'anonymous-reference',
    'referencia-an\u00f3nima': 'anonymous-reference',
    'referencia-nota-al-pie': 'footnote-reference',
    'referencia-cita': 'citation-reference',
    'referencia-sustitucion': 'substitution-reference',
    'referencia-sustituci\u00f3n': 'substitution-reference',
    'destino': 'target',
    'referencia-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'sin-analisis': 'raw',
    'sin-an\u00e1lisis': 'raw',
}
"""Mapping of Spanish role names to canonical role names for interpreted text.
"""
