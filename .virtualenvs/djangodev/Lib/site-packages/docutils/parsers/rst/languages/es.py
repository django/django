# $Id: es.py 9452 2023-09-27 00:11:54Z milde $
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
    'atención': 'attention',
    'atencion': 'attention',
    'precaución': 'caution',
    'code (translation required)': 'code',
    'precaucion': 'caution',
    'peligro': 'danger',
    'error': 'error',
    'sugerencia': 'hint',
    'importante': 'important',
    'nota': 'note',
    'consejo': 'tip',
    'advertencia': 'warning',
    'aviso': 'admonition',
    'exhortacion': 'admonition',  # sic! kept for backwards compatibiltity
    'exhortación': 'admonition',  # sic! kept for backwards compatibiltity
    'nota-al-margen': 'sidebar',
    'tema': 'topic',
    'bloque-de-lineas': 'line-block',
    'bloque-de-líneas': 'line-block',
    'literal-evaluado': 'parsed-literal',
    'firma': 'rubric',
    'epígrafe': 'epigraph',
    'epigrafe': 'epigraph',
    'destacado': 'highlights',
    'cita-destacada': 'pull-quote',
    'combinacion': 'compound',
    'combinación': 'compound',
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
    'sin-análisis': 'raw',
    'reemplazar': 'replace',
    'unicode': 'unicode',
    'fecha': 'date',
    'clase': 'class',
    'rol': 'role',
    'rol-por-omision': 'default-role',
    'rol-por-omisión': 'default-role',
    'titulo': 'title',
    'título': 'title',
    'contenido': 'contents',
    'numseccion': 'sectnum',
    'numsección': 'sectnum',
    'numeracion-seccion': 'sectnum',
    'numeración-sección': 'sectnum',
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
    'subíndice': 'subscript',
    'superindice': 'superscript',
    'superíndice': 'superscript',
    'referencia-titulo': 'title-reference',
    'titulo': 'title-reference',
    't': 'title-reference',
    'referencia-pep': 'pep-reference',
    'pep': 'pep-reference',
    'referencia-rfc': 'rfc-reference',
    'rfc': 'rfc-reference',
    'enfasis': 'emphasis',
    'énfasis': 'emphasis',
    'destacado': 'strong',
    'literal': 'literal',  # "literal" is also a word in Spanish :-)
    'math (translation required)': 'math',
    'referencia-con-nombre': 'named-reference',
    'referencia-anonima': 'anonymous-reference',
    'referencia-anónima': 'anonymous-reference',
    'referencia-nota-al-pie': 'footnote-reference',
    'referencia-cita': 'citation-reference',
    'referencia-sustitucion': 'substitution-reference',
    'referencia-sustitución': 'substitution-reference',
    'destino': 'target',
    'referencia-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'sin-analisis': 'raw',
    'sin-análisis': 'raw',
}
"""Mapping of Spanish role names to canonical role names for interpreted text.
"""
