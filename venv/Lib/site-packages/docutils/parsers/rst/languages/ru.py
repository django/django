# $Id: ru.py 9030 2022-03-05 23:28:32Z milde $
# Author: Roman Suzi <rnd@onego.ru>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Russian-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'

directives = {
    'блок-строк': 'line-block',
    'meta': 'meta',
    'математика': 'math',
    'обработанный-литерал': 'parsed-literal',
    'выделенная-цитата': 'pull-quote',
    'код': 'code',
    'compound (translation required)': 'compound',
    'контейнер': 'container',
    'таблица': 'table',
    'csv-table (translation required)': 'csv-table',
    'list-table (translation required)': 'list-table',
    'сырой': 'raw',
    'замена': 'replace',
    'тестовая-директива-restructuredtext': 'restructuredtext-test-directive',
    'целевые-сноски': 'target-notes',
    'unicode': 'unicode',
    'дата': 'date',
    'боковая-полоса': 'sidebar',
    'важно': 'important',
    'включать': 'include',
    'внимание': 'attention',
    'выделение': 'highlights',
    'замечание': 'admonition',
    'изображение': 'image',
    'класс': 'class',
    'роль': 'role',
    'default-role (translation required)': 'default-role',
    'титул': 'title',
    'номер-раздела': 'sectnum',
    'нумерация-разделов': 'sectnum',
    'опасно': 'danger',
    'осторожно': 'caution',
    'ошибка': 'error',
    'подсказка': 'tip',
    'предупреждение': 'warning',
    'примечание': 'note',
    'рисунок': 'figure',
    'рубрика': 'rubric',
    'совет': 'hint',
    'содержание': 'contents',
    'тема': 'topic',
    'эпиграф': 'epigraph',
    'header (translation required)': 'header',
    'footer (translation required)': 'footer',
    }
"""Russian name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    'акроним': 'acronym',
    'код': 'code',
    'анонимная-ссылка': 'anonymous-reference',
    'буквально': 'literal',
    'математика': 'math',
    'верхний-индекс': 'superscript',
    'выделение': 'emphasis',
    'именованная-ссылка': 'named-reference',
    'индекс': 'index',
    'нижний-индекс': 'subscript',
    'сильное-выделение': 'strong',
    'сокращение': 'abbreviation',
    'ссылка-замена': 'substitution-reference',
    'ссылка-на-pep': 'pep-reference',
    'ссылка-на-rfc': 'rfc-reference',
    'ссылка-на-uri': 'uri-reference',
    'ссылка-на-заглавие': 'title-reference',
    'ссылка-на-сноску': 'footnote-reference',
    'цитатная-ссылка': 'citation-reference',
    'цель': 'target',
    'сырой': 'raw',
    }
"""Mapping of Russian role names to canonical role names for interpreted text.
"""
