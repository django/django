# $Id: fr.py 9030 2022-03-05 23:28:32Z milde $
# Author: Stefane Fermigier <sf@fermigier.com>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
French-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      'author': 'Auteur',
      'authors': 'Auteurs',
      'organization': 'Organisation',
      'address': 'Adresse',
      'contact': 'Contact',
      'version': 'Version',
      'revision': 'R\u00e9vision',
      'status': 'Statut',
      'date': 'Date',
      'copyright': 'Copyright',
      'dedication': 'D\u00e9dicace',
      'abstract': 'R\u00e9sum\u00e9',
      'attention': 'Attention!',
      'caution': 'Avertissement!',
      'danger': '!DANGER!',
      'error': 'Erreur',
      'hint': 'Indication',
      'important': 'Important',
      'note': 'Note',
      'tip': 'Astuce',
      'warning': 'Avis',
      'contents': 'Sommaire'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      'auteur': 'author',
      'auteurs': 'authors',
      'organisation': 'organization',
      'adresse': 'address',
      'contact': 'contact',
      'version': 'version',
      'r\u00e9vision': 'revision',
      'statut': 'status',
      'date': 'date',
      'copyright': 'copyright',
      'd\u00e9dicace': 'dedication',
      'r\u00e9sum\u00e9': 'abstract'}
"""French (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
