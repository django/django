# -*- coding: utf-8 -*-
# $Id: lt.py 7668 2013-06-04 12:46:30Z milde $
# Author: Dalius Dobravolskas <dalius.do...@gmail.com>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Lithuanian-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'dėmesio': 'attention',
      'atsargiai': 'caution',
      'code (translation required)': 'code',
      'pavojinga': 'danger',
      'klaida': 'error',
      'užuomina': 'hint',
      'svarbu': 'important',
      'pastaba': 'note',
      'patarimas': 'tip',
      'įspėjimas': 'warning',
      'perspėjimas': 'admonition',
      'šoninė-juosta': 'sidebar',
      'tema': 'topic',
      'linijinis-blokas': 'line-block',
      'išanalizuotas-literalas': 'parsed-literal',
      'rubrika': 'rubric',
      'epigrafas': 'epigraph',
      'pagridiniai-momentai': 'highlights',
      'atitraukta-citata': 'pull-quote',
      'sudėtinis-darinys': 'compound',
      'konteineris': 'container',
      #'questions': 'questions',
      'lentelė': 'table',
      'csv-lentelė': 'csv-table',
      'sąrašo-lentelė': 'list-table',
      #'qa': 'questions',
      #'faq': 'questions',
      'meta': 'meta',
      'matematika': 'math',
      #'imagemap': 'imagemap',
      'paveiksliukas': 'image',
      'iliustracija': 'figure',
      'pridėti': 'include',
      'žalia': 'raw',
      'pakeisti': 'replace',
      'unikodas': 'unicode',
      'data': 'date',
      'klasė': 'class',
      'rolė': 'role',
      'numatytoji-rolė': 'default-role',
      'titulas': 'title',
      'turinys': 'contents',
      'seknum': 'sectnum',
      'sekcijos-numeravimas': 'sectnum',
      'antraštė': 'header',
      'poraštė': 'footer',
      #'footnotes': 'footnotes',
      #'citations': 'citations',
      'nutaikytos-pastaba': 'target-notes',
      'restructuredtext-testinė-direktyva': 'restructuredtext-test-directive'}
"""Lithuanian name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'santrumpa': 'abbreviation',
    'sa': 'abbreviation',
    'akronimas': 'acronym',
    'ak': 'acronym',
    'code (translation required)': 'code',
    'indeksas': 'index',
    'i': 'index',
    'apatinis-indeksas': 'subscript',
    'sub': 'subscript',
    'viršutinis-indeksas': 'superscript',
    'sup': 'superscript',
    'antrašės-nuoroda': 'title-reference',
    'antraštė': 'title-reference',
    'a': 'title-reference',
    'pep-nuoroda': 'pep-reference',
    'pep': 'pep-reference',
    'rfc-nuoroda': 'rfc-reference',
    'rfc': 'rfc-reference',
    'paryškinimas': 'emphasis',
    'sustiprintas': 'strong',
    'literalas': 'literal',
    'matematika': 'math',
    'vardinė-nuoroda': 'named-reference',
    'anoniminė-nuoroda': 'anonymous-reference',
    'išnašos-nuoroda': 'footnote-reference',
    'citatos-nuoroda': 'citation-reference',
    'pakeitimo-nuoroda': 'substitution-reference',
    'taikinys': 'target',
    'uri-nuoroda': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'žalia': 'raw',}
"""Mapping of English role names to canonical role names for interpreted text.
"""
