# $Id$
# Author: Robert Wojciechowicz <rw@smsnet.pl>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Polish-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
    # language-dependent: fixed
    'uwaga': 'attention',
    'ostrożnie': 'caution',
    'code (translation required)': 'code',
    'niebezpieczeństwo': 'danger',
    'błąd': 'error',
    'wskazówka': 'hint',
    'ważne': 'important',
    'przypis': 'note',
    'rada': 'tip',
    'ostrzeżenie': 'warning',
    'zauważenie': 'admonition',  # remark
    'ramka': 'sidebar',
    'temat': 'topic',
    'blok-linii': 'line-block',
    'sparsowany-literał': 'parsed-literal',
    'rubryka': 'rubric',
    'epigraf': 'epigraph',
    'highlights': 'highlights',  # FIXME no polish equivalent?
    'pull-quote': 'pull-quote',  # FIXME no polish equivalent?
    'złożony': 'compound',
    'kontener': 'container',
    # 'questions': 'questions',
    'tabela': 'table',
    'tabela-csv': 'csv-table',
    'tabela-listowa': 'list-table',
    # 'qa': 'questions',
    # 'faq': 'questions',
    'meta': 'meta',
    'math (translation required)': 'math',
    # 'imagemap': 'imagemap',
    'obraz': 'image',
    'rycina': 'figure',
    'dołącz': 'include',
    'surowe': 'raw',
    'zastąp': 'replace',
    'unikod': 'unicode',
    'data': 'date',
    'klasa': 'class',
    'rola': 'role',
    'rola-domyślna': 'default-role',
    'tytuł': 'title',
    'treść': 'contents',
    'sectnum': 'sectnum',
    'numeracja-sekcji': 'sectnum',
    'nagłówek': 'header',
    'stopka': 'footer',
    # 'footnotes': 'footnotes',
    # 'citations': 'citations',
    'target-notes': 'target-notes',  # FIXME no polish equivalent?
    'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Polish name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'skrót': 'abbreviation',
    'akronim': 'acronym',
    'code (translation required)': 'code',
    'indeks': 'index',
    'indeks-dolny': 'subscript',
    'indeks-górny': 'superscript',
    'referencja-tytuł': 'title-reference',
    'referencja-pep': 'pep-reference',
    'referencja-rfc': 'rfc-reference',
    'podkreślenie': 'emphasis',
    'wytłuszczenie': 'strong',
    'dosłownie': 'literal',
    'math (translation required)': 'math',
    'referencja-nazwana': 'named-reference',
    'referencja-anonimowa': 'anonymous-reference',
    'referencja-przypis': 'footnote-reference',
    'referencja-cytat': 'citation-reference',
    'referencja-podstawienie': 'substitution-reference',
    'cel': 'target',
    'referencja-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'surowe': 'raw',
    }
"""Mapping of Polish role names to canonical role names for interpreted text.
"""
