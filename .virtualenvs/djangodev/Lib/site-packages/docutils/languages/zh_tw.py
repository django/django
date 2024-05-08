# $Id: zh_tw.py 9452 2023-09-27 00:11:54Z milde $
# Author: Joe YS Jaw <joeysj@users.sourceforge.net>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Traditional Chinese language mappings for language-dependent features.
"""

__docformat__ = 'reStructuredText'

labels = {
    # fixed: language-dependent
    'author': '作者',
    'authors': '作者群',
    'organization': '組織',
    'address': '地址',
    'contact': '連絡',
    'version': '版本',
    'revision': '修訂',
    'status': '狀態',
    'date': '日期',
    'copyright': '版權',
    'dedication': '題獻',
    'abstract': '摘要',
    'attention': '注意！',
    'caution': '小心！',
    'danger': '！危險！',
    'error': '錯誤',
    'hint': '提示',
    'important': '重要',
    'note': '註釋',
    'tip': '秘訣',
    'warning': '警告',
    'contents': '目錄',
    }
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'author (translation required)': 'author',
      'authors (translation required)': 'authors',
      'organization (translation required)': 'organization',
      'address (translation required)': 'address',
      'contact (translation required)': 'contact',
      'version (translation required)': 'version',
      'revision (translation required)': 'revision',
      'status (translation required)': 'status',
      'date (translation required)': 'date',
      'copyright (translation required)': 'copyright',
      'dedication (translation required)': 'dedication',
      'abstract (translation required)': 'abstract'}
"""Traditional Chinese to canonical name mapping for bibliographic fields."""

author_separators = [';', ',', '；', '，', '、']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
