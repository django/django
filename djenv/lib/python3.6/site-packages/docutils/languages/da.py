# -*- coding: utf-8 -*-
# $Id: da.py 7678 2013-07-03 09:57:36Z milde $
# Author: E D
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Danish-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Forfatter',
      'authors': 'Forfattere',
      'organization': 'Organisation',
      'address': 'Adresse',
      'contact': 'Kontakt',
      'version': 'Version',
      'revision': 'Revision',
      'status': 'Status',
      'date': 'Dato',
      'copyright': 'Copyright',
      'dedication': 'Dedikation',
      'abstract': 'Resumé',
      'attention': 'Giv agt!',
      'caution': 'Pas på!',
      'danger': '!FARE!',
      'error': 'Fejl',
      'hint': 'Vink',
      'important': 'Vigtigt',
      'note': 'Bemærk',
      'tip': 'Tips',
      'warning': 'Advarsel',
      'contents': 'Indhold'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'forfatter': 'author',
      'forfattere': 'authors',
      'organisation': 'organization',
      'adresse': 'address',
      'kontakt': 'contact',
      'version': 'version',
      'revision': 'revision',
      'status': 'status',
      'dato': 'date',
      'copyright': 'copyright',
      'dedikation': 'dedication',
      'resume': 'abstract',
      'resumé': 'abstract'}
"""Danish (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
