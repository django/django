# $Id: uk.py 9114 2022-07-28 17:06:10Z milde $
# Author: Dmytro Kazanzhy <dkazanzhy@gmail.com>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Ukrainian-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'

directives = {
    'блок-строк': 'line-block',
    'мета': 'meta',
    'математика': 'math',
    'оброблений-літерал': 'parsed-literal',
    'виділена-цитата': 'pull-quote',
    'код': 'code',
    'складений абзац': 'compound',
    'контейнер': 'container',
    'таблиця': 'table',
    'таблиця-csv': 'csv-table',
    'таблиця-списків': 'list-table',
    'сирий': 'raw',
    'заміна': 'replace',
    'тестова-директива-restructuredtext': 'restructuredtext-test-directive',
    'цільові-виноски': 'target-notes',
    'юнікод': 'unicode',
    'дата': 'date',
    'бічна-панель': 'sidebar',
    'важливо': 'important',
    'включати': 'include',
    'увага': 'attention',
    'виділення': 'highlights',
    'зауваження': 'admonition',
    'зображення': 'image',
    'клас': 'class',
    'роль': 'role',
    'роль-за-замовчуванням': 'default-role',
    'заголовок': 'title',
    'номер-розділу': 'sectnum',
    'нумерація-розділів': 'sectnum',
    'небезпечно': 'danger',
    'обережно': 'caution',
    'помилка': 'error',
    'підказка': 'tip',
    'попередження': 'warning',
    'примітка': 'note',
    'малюнок': 'figure',
    'рубрика': 'rubric',
    'порада': 'hint',
    'зміст': 'contents',
    'тема': 'topic',
    'епіграф': 'epigraph',
    'верхній колонтитул': 'header',
    'нижній колонтитул': 'footer',
    }
"""Ukrainian name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    'акронім': 'acronym',
    'код': 'code',
    'анонімне-посилання': 'anonymous-reference',
    'буквально': 'literal',
    'математика': 'math',
    'верхній-індекс': 'superscript',
    'наголос': 'emphasis',
    'іменоване-посилання': 'named-reference',
    'індекс': 'index',
    'нижній-індекс': 'subscript',
    'жирне-накреслення': 'strong',
    'скорочення': 'abbreviation',
    'посилання-заміна': 'substitution-reference',
    'посилання-на-pep': 'pep-reference',
    'посилання-на-rfc': 'rfc-reference',
    'посилання-на-uri': 'uri-reference',
    'посилання-на-заголовок': 'title-reference',
    'посилання-на-зноску': 'footnote-reference',
    'посилання-на-цитату': 'citation-reference',
    'ціль': 'target',
    'сирий': 'raw',
    }
"""Mapping of Ukrainian role names to canonical role names
for interpreted text.
"""
