# $Id: zh_tw.py 9030 2022-03-05 23:28:32Z milde $
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
      'author': '\u4f5c\u8005',  # '作者' <-- Chinese word
      'authors': '\u4f5c\u8005\u7fa4',  # '作者群',
      'organization': '\u7d44\u7e54',  # '組織',
      'address': '\u5730\u5740',  # '地址',
      'contact': '\u9023\u7d61',  # '連絡',
      'version': '\u7248\u672c',  # '版本',
      'revision': '\u4fee\u8a02',  # '修訂',
      'status': '\u72c0\u614b',  # '狀態',
      'date': '\u65e5\u671f',  # '日期',
      'copyright': '\u7248\u6b0a',  # '版權',
      'dedication': '\u984c\u737b',  # '題獻',
      'abstract': '\u6458\u8981',  # '摘要',
      'attention': '\u6ce8\u610f\uff01',  # '注意！',
      'caution': '\u5c0f\u5fc3\uff01',  # '小心！',
      'danger': '\uff01\u5371\u96aa\uff01',  # '！危險！',
      'error': '\u932f\u8aa4',  # '錯誤',
      'hint': '\u63d0\u793a',  # '提示',
      'important': '\u91cd\u8981',  # '注意！',
      'note': '\u8a3b\u91cb',  # '註釋',
      'tip': '\u79d8\u8a23',  # '秘訣',
      'warning': '\u8b66\u544a',  # '警告',
      'contents': '\u76ee\u9304',  # '目錄'
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

author_separators = [';', ',',
                     '\uff1b',  # '；'
                     '\uff0c',  # '，'
                     '\u3001',  # '、'
                     ]
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
