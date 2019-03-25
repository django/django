# $Id: fr.py 7119 2011-09-02 13:00:23Z milde $
# Authors: David Goodger <goodger@python.org>; William Dode
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
French-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      'attention': 'attention',
      'pr\u00E9caution': 'caution',
      'code': 'code',
      'danger': 'danger',
      'erreur': 'error',
      'conseil': 'hint',
      'important': 'important',
      'note': 'note',
      'astuce': 'tip',
      'avertissement': 'warning',
      'admonition': 'admonition',
      'encadr\u00E9': 'sidebar',
      'sujet': 'topic',
      'bloc-textuel': 'line-block',
      'bloc-interpr\u00E9t\u00E9': 'parsed-literal',
      'code-interpr\u00E9t\u00E9': 'parsed-literal',
      'intertitre': 'rubric',
      'exergue': 'epigraph',
      '\u00E9pigraphe': 'epigraph',
      'chapeau': 'highlights',
      'accroche': 'pull-quote',
      'compound (translation required)': 'compound',
      'container (translation required)': 'container',
      #u'questions': 'questions',
      #u'qr': 'questions',
      #u'faq': 'questions',
      'tableau': 'table',
      'csv-table (translation required)': 'csv-table',
      'list-table (translation required)': 'list-table',
      'm\u00E9ta': 'meta',
      'math (translation required)': 'math',
      #u'imagemap (translation required)': 'imagemap',
      'image': 'image',
      'figure': 'figure',
      'inclure': 'include',
      'brut': 'raw',
      'remplacer': 'replace',
      'remplace': 'replace',
      'unicode': 'unicode',
      'date': 'date',
      'classe': 'class',
      'role (translation required)': 'role',
      'default-role (translation required)': 'default-role',
      'titre (translation required)': 'title',
      'sommaire': 'contents',
      'table-des-mati\u00E8res': 'contents',
      'sectnum': 'sectnum',
      'section-num\u00E9rot\u00E9e': 'sectnum',
      'liens': 'target-notes',
      'header (translation required)': 'header',
      'footer (translation required)': 'footer',
      #u'footnotes (translation required)': 'footnotes',
      #u'citations (translation required)': 'citations',
      }
"""French name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
      'abr\u00E9viation': 'abbreviation',
      'acronyme': 'acronym',
      'sigle': 'acronym',
      'code': 'code',
      'index': 'index',
      'indice': 'subscript',
      'ind': 'subscript',
      'exposant': 'superscript',
      'exp': 'superscript',
      'titre-r\u00E9f\u00E9rence': 'title-reference',
      'titre': 'title-reference',
      'pep-r\u00E9f\u00E9rence': 'pep-reference',
      'rfc-r\u00E9f\u00E9rence': 'rfc-reference',
      'emphase': 'emphasis',
      'fort': 'strong',
      'litt\u00E9ral': 'literal',
    'math (translation required)': 'math',
      'nomm\u00E9e-r\u00E9f\u00E9rence': 'named-reference',
      'anonyme-r\u00E9f\u00E9rence': 'anonymous-reference',
      'note-r\u00E9f\u00E9rence': 'footnote-reference',
      'citation-r\u00E9f\u00E9rence': 'citation-reference',
      'substitution-r\u00E9f\u00E9rence': 'substitution-reference',
      'lien': 'target',
      'uri-r\u00E9f\u00E9rence': 'uri-reference',
      'brut': 'raw',}
"""Mapping of French role names to canonical role names for interpreted text.
"""
