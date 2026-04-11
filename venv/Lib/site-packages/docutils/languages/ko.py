# $Id: ko.py 9030 2022-03-05 23:28:32Z milde $
# Author: Thomas SJ Kang <thomas.kangsj@ujuc.kr>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Korean-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': '저자',
      'authors': '저자들',
      'organization': '조직',
      'address': '주소',
      'contact': '연락처',
      'version': '버전',
      'revision': '리비전',
      'status': '상태',
      'date': '날짜',
      'copyright': '저작권',
      'dedication': '헌정',
      'abstract': '요약',
      'attention': '집중!',
      'caution': '주의!',
      'danger': '!위험!',
      'error': '오류',
      'hint': '실마리',
      'important': '중요한',
      'note': '비고',
      'tip': '팁',
      'warning': '경고',
      'contents': '목차'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      '저자': 'author',
      '저자들': 'authors',
      '조직': 'organization',
      '주소': 'address',
      '연락처': 'contact',
      '버전': 'version',
      '리비전': 'revision',
      '상태': 'status',
      '날짜': 'date',
      '저작권': 'copyright',
      '헌정': 'dedication',
      '요약': 'abstract'}
"""Korean to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
