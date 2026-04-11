# $Id: ca.py 9457 2023-10-02 16:25:50Z milde $
# Authors: Ivan Vilata i Balaguer <ivan@selidor.net>;
#          Antoni Bella Pérez <antonibella5@yahoo.com>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation,
# please read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

# These translations can be used without changes for
# Valencian variant of Catalan (use language tag "ca-valencia").
# Checked by a native speaker of Valentian.

"""
Catalan-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      'atenció': 'attention',
      'compte': 'caution',
      'perill': 'danger',
      'error': 'error',
      'suggeriment': 'hint',
      'important': 'important',
      'nota': 'note',
      'consell': 'tip',
      'avís': 'warning',
      'advertiment': 'admonition',
      'nota-al-marge': 'sidebar',
      'nota-marge': 'sidebar',
      'tema': 'topic',
      'bloc-de-línies': 'line-block',
      'bloc-línies': 'line-block',
      'literal-analitzat': 'parsed-literal',
      'codi': 'code',
      'bloc-de-codi': 'code',
      'matemàtiques': 'math',
      'rúbrica': 'rubric',
      'epígraf': 'epigraph',
      'sumari': 'highlights',
      'cita-destacada': 'pull-quote',
      'compost': 'compound',
      'contenidor': 'container',
      'taula': 'table',
      'taula-csv': 'csv-table',
      'taula-llista': 'list-table',
      'meta': 'meta',
      # 'imagemap': 'imagemap',
      'imatge': 'image',
      'figura': 'figure',
      'inclou': 'include',
      'incloure': 'include',
      'cru': 'raw',
      'reemplaça': 'replace',
      'reemplaçar': 'replace',
      'unicode': 'unicode',
      'data': 'date',
      'classe': 'class',
      'rol': 'role',
      'rol-predeterminat': 'default-role',
      'títol': 'title',
      'contingut': 'contents',
      'numsec': 'sectnum',
      'numeració-de-seccions': 'sectnum',
      'numeració-seccions': 'sectnum',
      'capçalera': 'header',
      'peu-de-pàgina': 'footer',
      'peu-pàgina': 'footer',
      # 'footnotes': 'footnotes',
      # 'citations': 'citations',
      'notes-amb-destinacions': 'target-notes',
      'notes-destinacions': 'target-notes',
      'directiva-de-prova-de-restructuredtext': 'restructuredtext-test-directive'}  # noqa:E501
"""Catalan name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'abreviatura': 'abbreviation',
    'abreviació': 'abbreviation',
    'abrev': 'abbreviation',
    'ab': 'abbreviation',
    'acrònim': 'acronym',
    'ac': 'acronym',
    'codi': 'code',
    'èmfasi': 'emphasis',
    'literal': 'literal',
    'matemàtiques': 'math',
    'referència-a-pep': 'pep-reference',
    'referència-pep': 'pep-reference',
    'pep': 'pep-reference',
    'referència-a-rfc': 'rfc-reference',
    'referència-rfc': 'rfc-reference',
    'rfc': 'rfc-reference',
    'destacat': 'strong',
    'subíndex': 'subscript',
    'sub': 'subscript',
    'superíndex': 'superscript',
    'sup': 'superscript',
    'referència-a-títol': 'title-reference',
    'referència-títol': 'title-reference',
    'títol': 'title-reference',
    't': 'title-reference',
    'cru': 'raw',
    # the following roles are not implemented in Docutils
    'índex': 'index',
    'i': 'index',
    'referència-anònima': 'anonymous-reference',
    'referència-a-cita': 'citation-reference',
    'referència-cita': 'citation-reference',
    'referència-a-nota-al-peu': 'footnote-reference',
    'referència-nota-al-peu': 'footnote-reference',
    'referència-amb-nom': 'named-reference',
    'referència-nom': 'named-reference',
    'referència-a-substitució': 'substitution-reference',
    'referència-substitució': 'substitution-reference',
    'referència-a-uri': 'uri-reference',
    'referència-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'destinació': 'target',
    }
"""Mapping of Catalan role names to canonical role names for interpreted text.
"""
