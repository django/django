# $Id$
# Author: Robert Wojciechowicz <rw@smsnet.pl>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Polish-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'uwaga': 'attention',
      'ostro\u017cnie': 'caution',
      'code (translation required)': 'code',
      'niebezpiecze\u0144stwo': 'danger',
      'b\u0142\u0105d': 'error',
      'wskaz\u00f3wka': 'hint',
      'wa\u017cne': 'important',
      'przypis': 'note',
      'rada': 'tip',
      'ostrze\u017cenie': 'warning',
      'upomnienie': 'admonition',
      'ramka': 'sidebar',
      'temat': 'topic',
      'blok-linii': 'line-block',
      'sparsowany-litera\u0142': 'parsed-literal',
      'rubryka': 'rubric',
      'epigraf': 'epigraph',
      'highlights': 'highlights',  # FIXME no polish equivalent?
      'pull-quote': 'pull-quote',  # FIXME no polish equivalent?
      'z\u0142o\u017cony': 'compound',
      'kontener': 'container',
      #'questions': 'questions',
      'tabela': 'table',
      'tabela-csv': 'csv-table',
      'tabela-listowa': 'list-table',
      #'qa': 'questions',
      #'faq': 'questions',
      'meta': 'meta',
      'math (translation required)': 'math',
      #'imagemap': 'imagemap',
      'obraz': 'image',
      'rycina': 'figure',
      'do\u0142\u0105cz': 'include',
      'surowe': 'raw',
      'zast\u0105p': 'replace',
      'unikod': 'unicode',
      'data': 'date',
      'klasa': 'class',
      'rola': 'role',
      'rola-domy\u015blna': 'default-role',
      'tytu\u0142': 'title',
      'tre\u015b\u0107': 'contents',
      'sectnum': 'sectnum',
      'numeracja-sekcji': 'sectnum',
      'nag\u0142\u00f3wek': 'header',
      'stopka': 'footer',
      #'footnotes': 'footnotes',
      #'citations': 'citations',
      'target-notes': 'target-notes',  # FIXME no polish equivalent?
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Polish name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'skr\u00f3t': 'abbreviation',
    'akronim': 'acronym',
    'code (translation required)': 'code',
    'indeks': 'index',
    'indeks-dolny': 'subscript',
    'indeks-g\u00f3rny': 'superscript',
    'referencja-tytu\u0142': 'title-reference',
    'referencja-pep': 'pep-reference',
    'referencja-rfc': 'rfc-reference',
    'podkre\u015blenie': 'emphasis',
    'wyt\u0142uszczenie': 'strong',
    'dos\u0142ownie': 'literal',
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
    'surowe': 'raw',}
"""Mapping of Polish role names to canonical role names for interpreted text.
"""
    

                 
