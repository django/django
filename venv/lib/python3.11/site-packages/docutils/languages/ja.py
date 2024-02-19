# $Id: ja.py 9030 2022-03-05 23:28:32Z milde $
# Author: Hisashi Morita <hisashim@kt.rim.or.jp>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Japanese-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': '著者',
      'authors': '著者',
      'organization': '組織',
      'address': '住所',
      'contact': '連絡先',
      'version': 'バージョン',
      'revision': 'リビジョン',
      'status': 'ステータス',
      'date': '日付',
      'copyright': '著作権',
      'dedication': '献辞',
      'abstract': '概要',
      'attention': '注目!',
      'caution': '注意!',
      'danger': '!危険!',
      'error': 'エラー',
      'hint': 'ヒント',
      'important': '重要',
      'note': '備考',
      'tip': '通報',
      'warning': '警告',
      'contents': '目次'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      '著者': 'author',
      ' n/a': 'authors',
      '組織': 'organization',
      '住所': 'address',
      '連絡先': 'contact',
      'バージョン': 'version',
      'リビジョン': 'revision',
      'ステータス': 'status',
      '日付': 'date',
      '著作権': 'copyright',
      '献辞': 'dedication',
      '概要': 'abstract'}
"""Japanese (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
