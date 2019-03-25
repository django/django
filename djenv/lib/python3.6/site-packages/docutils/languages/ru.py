# -*- coding: utf-8 -*-
# $Id: ru.py 7125 2011-09-16 18:36:18Z milde $
# Author: Roman Suzi <rnd@onego.ru>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Russian-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      'abstract': 'Аннотация',
      'address': 'Адрес',
      'attention': 'Внимание!',
      'author': 'Автор',
      'authors': 'Авторы',
      'caution': 'Осторожно!',
      'contact': 'Контакт',
      'contents': 'Содержание',
      'copyright': 'Права копирования',
      'danger': 'ОПАСНО!',
      'date': 'Дата',
      'dedication': 'Посвящение',
      'error': 'Ошибка',
      'hint': 'Совет',
      'important': 'Важно',
      'note': 'Примечание',
      'organization': 'Организация',
      'revision': 'Редакция',
      'status': 'Статус',
      'tip': 'Подсказка',
      'version': 'Версия',
      'warning': 'Предупреждение'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      'аннотация': 'abstract',
      'адрес': 'address',
      'автор': 'author',
      'авторы': 'authors',
      'контакт': 'contact',
      'права копирования': 'copyright',
      'дата': 'date',
      'посвящение': 'dedication',
      'организация': 'organization',
      'редакция': 'revision',
      'статус': 'status',
      'версия': 'version'}
"""Russian (lowcased) to canonical name mapping for bibliographic fields."""

author_separators =  [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
