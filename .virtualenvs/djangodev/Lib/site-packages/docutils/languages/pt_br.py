# $Id: pt_br.py 9452 2023-09-27 00:11:54Z milde $
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
      'organization': 'Organização',
      'address': 'Endereço',
      'contact': 'Contato',
      'version': 'Versão',
      'revision': 'Revisão',
      'status': 'Estado',
      'date': 'Data',
      'copyright': 'Copyright',
      'dedication': 'Dedicatória',
      'abstract': 'Resumo',
      'attention': 'Atenção!',
      'caution': 'Cuidado!',
      'danger': 'PERIGO!',
      'error': 'Erro',
      'hint': 'Sugestão',
      'important': 'Importante',
      'note': 'Nota',
      'tip': 'Dica',
      'warning': 'Aviso',
      'contents': 'Sumário'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'autor': 'author',
      'autores': 'authors',
      'organização': 'organization',
      'endereço': 'address',
      'contato': 'contact',
      'versão': 'version',
      'revisão': 'revision',
      'estado': 'status',
      'data': 'date',
      'copyright': 'copyright',
      'dedicatória': 'dedication',
      'resumo': 'abstract'}
"""Brazilian Portuguese (lowcased) name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
