# $Id: pt_br.py 9030 2022-03-05 23:28:32Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Brazilian Portuguese-language mappings for language-dependent features.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Autor',
      'authors': 'Autores',
      'organization': 'Organiza\u00E7\u00E3o',
      'address': 'Endere\u00E7o',
      'contact': 'Contato',
      'version': 'Vers\u00E3o',
      'revision': 'Revis\u00E3o',
      'status': 'Estado',
      'date': 'Data',
      'copyright': 'Copyright',
      'dedication': 'Dedicat\u00F3ria',
      'abstract': 'Resumo',
      'attention': 'Aten\u00E7\u00E3o!',
      'caution': 'Cuidado!',
      'danger': 'PERIGO!',
      'error': 'Erro',
      'hint': 'Sugest\u00E3o',
      'important': 'Importante',
      'note': 'Nota',
      'tip': 'Dica',
      'warning': 'Aviso',
      'contents': 'Sum\u00E1rio'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autor': 'author',
      'autores': 'authors',
      'organiza\u00E7\u00E3o': 'organization',
      'endere\u00E7o': 'address',
      'contato': 'contact',
      'vers\u00E3o': 'version',
      'revis\u00E3o': 'revision',
      'estado': 'status',
      'data': 'date',
      'copyright': 'copyright',
      'dedicat\u00F3ria': 'dedication',
      'resumo': 'abstract'}
"""Brazilian Portuguese (lowcased) name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
