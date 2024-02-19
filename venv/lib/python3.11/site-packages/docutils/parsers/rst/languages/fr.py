# $Id: fr.py 9383 2023-05-11 15:01:20Z milde $
# Authors: David Goodger <goodger@python.org>; William Dode
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
French-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      'attention': 'attention',
      'précaution': 'caution',
      'danger': 'danger',
      'erreur': 'error',
      'conseil': 'hint',
      'important': 'important',
      'note': 'note',
      'astuce': 'tip',
      'avertissement': 'warning',
      'admonition': 'admonition',  # sic! Not used in this sense in rST.
      # suggestions: annonce, avis, indication, remarque, renseignement
      # see also https://sourceforge.net/p/docutils/bugs/453/
      'encadré': 'sidebar',
      'sujet': 'topic',
      'bloc-textuel': 'line-block',
      'bloc-interprété': 'parsed-literal',
      'code-interprété': 'parsed-literal',
      'code': 'code',
      'math (translation required)': 'math',
      'intertitre': 'rubric',
      'exergue': 'epigraph',
      'épigraphe': 'epigraph',
      'chapeau': 'highlights',
      'accroche': 'pull-quote',
      'compound (translation required)': 'compound',
      'container (translation required)': 'container',
      'tableau': 'table',
      'csv-table (translation required)': 'csv-table',
      'list-table (translation required)': 'list-table',
      'méta': 'meta',
      # 'imagemap (translation required)': 'imagemap',
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
      'table-des-matières': 'contents',
      'sectnum': 'sectnum',
      'section-numérotée': 'sectnum',
      'liens': 'target-notes',
      'header (translation required)': 'header',
      'footer (translation required)': 'footer',
      # 'footnotes (translation required)': 'footnotes',
      # 'citations (translation required)': 'citations',
      }
"""Mapping of French directive names to registered directive names

Cf. https://docutils.sourceforge.io/docs/ref/rst/directives.html
and `_directive_registry` in ``directives/__init__.py``.
"""

roles = {
      'abréviation': 'abbreviation',
      'acronyme': 'acronym',
      'sigle': 'acronym',
      'code': 'code',
      'emphase': 'emphasis',
      'littéral': 'literal',
      'math (translation required)': 'math',
      'pep-référence': 'pep-reference',
      'rfc-référence': 'rfc-reference',
      'fort': 'strong',
      'indice': 'subscript',
      'ind': 'subscript',
      'exposant': 'superscript',
      'exp': 'superscript',
      'titre-référence': 'title-reference',
      'titre': 'title-reference',
      'brut': 'raw',
      # the following roles are not implemented in Docutils
      'index': 'index',
      'nommée-référence': 'named-reference',
      'anonyme-référence': 'anonymous-reference',
      'note-référence': 'footnote-reference',
      'citation-référence': 'citation-reference',
      'substitution-référence': 'substitution-reference',
      'lien': 'target',
      'uri-référence': 'uri-reference',
      }
"""Mapping of French role names to canonical role names for interpreted text.
"""
