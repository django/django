# $Id: eo.py 9030 2022-03-05 23:28:32Z milde $
# Author: Marcelo Huerta San Martin <richieadler@users.sourceforge.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Esperanto-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'atentu': 'attention',
      'zorgu': 'caution',
      'code (translation required)': 'code',
      'dangxero': 'danger',
      'dan\u011dero': 'danger',
      'eraro': 'error',
      'spuro': 'hint',
      'grava': 'important',
      'noto': 'note',
      'helpeto': 'tip',
      'averto': 'warning',
      'admono': 'admonition',
      'flankteksto': 'sidebar',
      'temo': 'topic',
      'linea-bloko': 'line-block',
      'analizota-literalo': 'parsed-literal',
      'rubriko': 'rubric',
      'epigrafo': 'epigraph',
      'elstarajxoj': 'highlights',
      'elstara\u0135oj': 'highlights',
      'ekstera-citajxo': 'pull-quote',
      'ekstera-cita\u0135o': 'pull-quote',
      'kombinajxo': 'compound',
      'kombina\u0135o': 'compound',
      'tekstingo': 'container',
      'enhavilo': 'container',
      # 'questions': 'questions',
      # 'qa': 'questions',
      # 'faq': 'questions',
      'tabelo': 'table',
      'tabelo-vdk': 'csv-table',  # "valoroj disigitaj per komoj"
      'tabelo-csv': 'csv-table',
      'tabelo-lista': 'list-table',
      'meta': 'meta',
      'math (translation required)': 'math',
      # 'imagemap': 'imagemap',
      'bildo': 'image',
      'figuro': 'figure',
      'inkludi': 'include',
      'senanaliza': 'raw',
      'anstatauxi': 'replace',
      'anstata\u016di': 'replace',
      'unicode': 'unicode',
      'dato': 'date',
      'klaso': 'class',
      'rolo': 'role',
      'preterlasita-rolo': 'default-role',
      'titolo': 'title',
      'enhavo': 'contents',
      'seknum': 'sectnum',
      'sekcia-numerado': 'sectnum',
      'kapsekcio': 'header',
      'piedsekcio': 'footer',
      # 'footnotes': 'footnotes',
      # 'citations': 'citations',
      'celaj-notoj': 'target-notes',
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Esperanto name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'mallongigo': 'abbreviation',
    'mall': 'abbreviation',
    'komenclitero': 'acronym',
    'kl': 'acronym',
    'code (translation required)': 'code',
    'indekso': 'index',
    'i': 'index',
    'subskribo': 'subscript',
    'sub': 'subscript',
    'supraskribo': 'superscript',
    'sup': 'superscript',
    'titola-referenco': 'title-reference',
    'titolo': 'title-reference',
    't': 'title-reference',
    'pep-referenco': 'pep-reference',
    'pep': 'pep-reference',
    'rfc-referenco': 'rfc-reference',
    'rfc': 'rfc-reference',
    'emfazo': 'emphasis',
    'forta': 'strong',
    'litera': 'literal',
    'math (translation required)': 'math',
    'nomita-referenco': 'named-reference',
    'nenomita-referenco': 'anonymous-reference',
    'piednota-referenco': 'footnote-reference',
    'citajxo-referenco': 'citation-reference',
    'cita\u0135o-referenco': 'citation-reference',
    'anstatauxa-referenco': 'substitution-reference',
    'anstata\u016da-referenco': 'substitution-reference',
    'celo': 'target',
    'uri-referenco': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'senanaliza': 'raw',
}
"""Mapping of Esperanto role names to canonical names for interpreted text.
"""
