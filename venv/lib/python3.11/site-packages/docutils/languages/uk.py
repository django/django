# $Id: uk.py 9114 2022-07-28 17:06:10Z milde $
# Author: Dmytro Kazanzhy <dkazanzhy@gmail.com>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Ukrainian-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      'abstract': 'Анотація',
      'address': 'Адреса',
      'attention': 'Увага!',
      'author': 'Автор',
      'authors': 'Автори',
      'caution': 'Обережно!',
      'contact': 'Контакт',
      'contents': 'Зміст',
      'copyright': 'Права копіювання',
      'danger': 'НЕБЕЗПЕЧНО!',
      'date': 'Дата',
      'dedication': 'Посвячення',
      'error': 'Помилка',
      'hint': 'Порада',
      'important': 'Важливо',
      'note': 'Примітка',
      'organization': 'Організація',
      'revision': 'Редакція',
      'status': 'Статус',
      'tip': 'Підказка',
      'version': 'Версія',
      'warning': 'Попередження'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      'анотація': 'abstract',
      'адреса': 'address',
      'автор': 'author',
      'автори': 'authors',
      'контакт': 'contact',
      'права копіювання': 'copyright',
      'дата': 'date',
      'посвячення': 'dedication',
      'організація': 'organization',
      'редакція': 'revision',
      'статус': 'status',
      'версія': 'version'}
"""Ukrainian (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
