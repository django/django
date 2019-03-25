# -*- coding: utf-8 -*-
# $Id: es.py 4572 2006-05-25 20:48:37Z richieadler $
# Author: Marcelo Huerta San Martín <richieadler@users.sourceforge.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Spanish-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      'author': 'Autor',
      'authors': 'Autores',
      'organization': 'Organizaci\u00f3n',
      'address': 'Direcci\u00f3n',
      'contact': 'Contacto',
      'version': 'Versi\u00f3n',
      'revision': 'Revisi\u00f3n',
      'status': 'Estado',
      'date': 'Fecha',
      'copyright': 'Copyright',
      'dedication': 'Dedicatoria',
      'abstract': 'Resumen',
      'attention': '\u00a1Atenci\u00f3n!',
      'caution': '\u00a1Precauci\u00f3n!',
      'danger': '\u00a1PELIGRO!',
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
      'organizaci\u00f3n': 'organization',
      'direcci\u00f3n': 'address',
      'contacto': 'contact',
      'versi\u00f3n': 'version',
      'revisi\u00f3n': 'revision',
      'estado': 'status',
      'fecha': 'date',
      'copyright': 'copyright',
      'dedicatoria': 'dedication',
      'resumen': 'abstract'}
"""Spanish (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
