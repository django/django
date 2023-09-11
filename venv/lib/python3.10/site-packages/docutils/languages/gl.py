# Author: David Goodger
# Contact: goodger@users.sourceforge.net
# Revision: $Revision: 2224 $
# Date: $Date: 2004-06-05 21:40:46 +0200 (Sat, 05 Jun 2004) $
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Galician-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Autor',
      'authors': 'Autores',
      'organization': 'Organizaci\u00f3n',
      'address': 'Enderezo',
      'contact': 'Contacto',
      'version': 'Versi\u00f3n',
      'revision': 'Revisi\u00f3n',
      'status': 'Estado',
      'date': 'Data',
      'copyright': 'Dereitos de copia',
      'dedication': 'Dedicatoria',
      'abstract': 'Abstract',
      'attention': 'Atenci\u00f3n!',
      'caution': 'Advertencia!',
      'danger': 'PERIGO!',
      'error': 'Erro',
      'hint': 'Consello',
      'important': 'Importante',
      'note': 'Nota',
      'tip': 'Suxesti\u00f3n',
      'warning': 'Aviso',
      'contents': 'Contido'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autor': 'author',
      'autores': 'authors',
      'organizaci\u00f3n': 'organization',
      'enderezo': 'address',
      'contacto': 'contact',
      'versi\u00f3n': 'version',
      'revisi\u00f3n': 'revision',
      'estado': 'status',
      'data': 'date',
      'dereitos de copia': 'copyright',
      'dedicatoria': 'dedication',
      'abstract': 'abstract'}
"""Galician (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
