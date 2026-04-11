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
      'organization': 'Organización',
      'address': 'Enderezo',
      'contact': 'Contacto',
      'version': 'Versión',
      'revision': 'Revisión',
      'status': 'Estado',
      'date': 'Data',
      'copyright': 'Dereitos de copia',
      'dedication': 'Dedicatoria',
      'abstract': 'Abstract',
      'attention': 'Atención!',
      'caution': 'Advertencia!',
      'danger': 'PERIGO!',
      'error': 'Erro',
      'hint': 'Consello',
      'important': 'Importante',
      'note': 'Nota',
      'tip': 'Suxestión',
      'warning': 'Aviso',
      'contents': 'Contido'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autor': 'author',
      'autores': 'authors',
      'organización': 'organization',
      'enderezo': 'address',
      'contacto': 'contact',
      'versión': 'version',
      'revisión': 'revision',
      'estado': 'status',
      'data': 'date',
      'dereitos de copia': 'copyright',
      'dedicatoria': 'dedication',
      'abstract': 'abstract'}
"""Galician (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
