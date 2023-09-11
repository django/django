# $Id: ko.py 9030 2022-03-05 23:28:32Z milde $
# Author: Thomas SJ Kang <thomas.kangsj@ujuc.kr>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Korean-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      '집중': 'attention',
      '주의': 'caution',
      '코드': 'code',
      '코드-블록': 'code',
      '소스코드': 'code',
      '위험': 'danger',
      '오류': 'error',
      '실마리': 'hint',
      '중요한': 'important',
      '비고': 'note',
      '팁': 'tip',
      '경고': 'warning',
      '권고': 'admonition',
      '사이드바': 'sidebar',
      '주제': 'topic',
      '라인-블록': 'line-block',
      '파싱된-리터럴': 'parsed-literal',
      '지시문': 'rubric',
      '제명': 'epigraph',
      '하이라이트': 'highlights',
      '발췌문': 'pull-quote',
      '합성어': 'compound',
      '컨테이너': 'container',
      # '질문': 'questions',
      '표': 'table',
      'csv-표': 'csv-table',
      'list-표': 'list-table',
      # 'qa': 'questions',
      # 'faq': 'questions',
      '메타': 'meta',
      '수학': 'math',
      # '이미지맵': 'imagemap',
      '이미지': 'image',
      '도표': 'figure',
      '포함': 'include',
      'raw': 'raw',
      '대신하다': 'replace',
      '유니코드': 'unicode',
      '날짜': 'date',
      '클래스': 'class',
      '역할': 'role',
      '기본-역할': 'default-role',
      '제목': 'title',
      '내용': 'contents',
      'sectnum': 'sectnum',
      '섹션-번호-매기기': 'sectnum',
      '머리말': 'header',
      '꼬리말': 'footer',
      # '긱주': 'footnotes',
      # '인용구': 'citations',
      '목표-노트': 'target-notes',
      'restructuredtext 테스트 지시어': 'restructuredtext-test-directive'}
"""Korean name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    '약어': 'abbreviation',
    'ab': 'abbreviation',
    '두음문자': 'acronym',
    'ac': 'acronym',
    '코드': 'code',
    '색인': 'index',
    'i': 'index',
    '다리-글자': 'subscript',
    'sub': 'subscript',
    '어깨-글자': 'superscript',
    'sup': 'superscript',
    '제목-참조': 'title-reference',
    '제목': 'title-reference',
    't': 'title-reference',
    'pep-참조': 'pep-reference',
    'pep': 'pep-reference',
    'rfc-참조': 'rfc-reference',
    'rfc': 'rfc-reference',
    '강조': 'emphasis',
    '굵게': 'strong',
    '기울기': 'literal',
    '수학': 'math',
    '명명된-참조': 'named-reference',
    '익명-참조': 'anonymous-reference',
    '각주-참조': 'footnote-reference',
    '인용-참조': 'citation-reference',
    '대리-참조': 'substitution-reference',
    '대상': 'target',
    'uri-참조': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'raw': 'raw',
    }
"""Mapping of Korean role names to canonical role names for interpreted text.
"""
