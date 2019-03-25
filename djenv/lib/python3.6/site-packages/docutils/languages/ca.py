# $Id: ca.py 4564 2006-05-21 20:44:42Z wiemann $
# Author: Ivan Vilata i Balaguer <ivan@selidor.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Catalan-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Autor',
      'authors': 'Autors',
      'organization': 'Organitzaci\u00F3',
      'address': 'Adre\u00E7a',
      'contact': 'Contacte',
      'version': 'Versi\u00F3',
      'revision': 'Revisi\u00F3',
      'status': 'Estat',
      'date': 'Data',
      'copyright': 'Copyright',
      'dedication': 'Dedicat\u00F2ria',
      'abstract': 'Resum',
      'attention': 'Atenci\u00F3!',
      'caution': 'Compte!',
      'danger': 'PERILL!',
      'error': 'Error',
      'hint': 'Suggeriment',
      'important': 'Important',
      'note': 'Nota',
      'tip': 'Consell',
      'warning': 'Av\u00EDs',
      'contents': 'Contingut'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autor': 'author',
      'autors': 'authors',
      'organitzaci\u00F3': 'organization',
      'adre\u00E7a': 'address',
      'contacte': 'contact',
      'versi\u00F3': 'version',
      'revisi\u00F3': 'revision',
      'estat': 'status',
      'data': 'date',
      'copyright': 'copyright',
      'dedicat\u00F2ria': 'dedication',
      'resum': 'abstract'}
"""Catalan (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
