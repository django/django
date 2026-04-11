# $Id: fr.py 9452 2023-09-27 00:11:54Z milde $
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
      'revision': 'Révision',
      'status': 'Statut',
      'date': 'Date',
      'copyright': 'Copyright',
      'dedication': 'Dédicace',
      'abstract': 'Résumé',
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
      'révision': 'revision',
      'statut': 'status',
      'date': 'date',
      'copyright': 'copyright',
      'dédicace': 'dedication',
      'résumé': 'abstract'}
"""French (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
