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
Catalan-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Autor',
      'authors': 'Autors',
      'organization': 'Organització',
      'address': 'Adreça',
      'contact': 'Contacte',
      'version': 'Versió',
      'revision': 'Revisió',
      'status': 'Estat',
      'date': 'Data',
      'copyright': 'Copyright',
      'dedication': 'Dedicatòria',
      'abstract': 'Resum',
      'attention': 'Atenció!',
      'caution': 'Compte!',
      'danger': 'PERILL!',
      'error': 'Error',
      'hint': 'Suggeriment',
      'important': 'Important',
      'note': 'Nota',
      'tip': 'Consell',
      'warning': 'Avís',
      'contents': 'Contingut'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autor': 'author',
      'autors': 'authors',
      'organització': 'organization',
      'adreça': 'address',
      'contacte': 'contact',
      'versió': 'version',
      'revisió': 'revision',
      'estat': 'status',
      'data': 'date',
      'copyright': 'copyright',
      'dedicatòria': 'dedication',
      'resum': 'abstract'}
"""Catalan (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
