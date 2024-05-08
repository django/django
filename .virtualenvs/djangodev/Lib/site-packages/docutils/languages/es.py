# $Id: es.py 9452 2023-09-27 00:11:54Z milde $
# Author: Marcelo Huerta San Martín <richieadler@users.sourceforge.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Spanish-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      'author': 'Autor',
      'authors': 'Autores',
      'organization': 'Organización',
      'address': 'Dirección',
      'contact': 'Contacto',
      'version': 'Versión',
      'revision': 'Revisión',
      'status': 'Estado',
      'date': 'Fecha',
      'copyright': 'Copyright',
      'dedication': 'Dedicatoria',
      'abstract': 'Resumen',
      'attention': '¡Atención!',
      'caution': '¡Precaución!',
      'danger': '¡PELIGRO!',
      'error': 'Error',
      'hint': 'Sugerencia',
      'important': 'Importante',
      'note': 'Nota',
      'tip': 'Consejo',
      'warning': 'Advertencia',
      'contents': 'Contenido'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      'autor': 'author',
      'autores': 'authors',
      'organización': 'organization',
      'dirección': 'address',
      'contacto': 'contact',
      'versión': 'version',
      'revisión': 'revision',
      'estado': 'status',
      'fecha': 'date',
      'copyright': 'copyright',
      'dedicatoria': 'dedication',
      'resumen': 'abstract'}
"""Spanish (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
