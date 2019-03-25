# -*- coding: utf-8 -*-
# $Id: zh_cn.py 7119 2011-09-02 13:00:23Z milde $
# Author: Panjunyong <panjy@zopechina.com>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Simplified Chinese language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
      # language-dependent: fixed
      '注意': 'attention',
      '小心': 'caution',
      'code (translation required)': 'code',
      '危险': 'danger',
      '错误': 'error',
      '提示': 'hint',
      '重要': 'important',
      '注解': 'note',
      '技巧': 'tip',
      '警告': 'warning',
      '忠告': 'admonition',
      '侧框': 'sidebar',
      '主题': 'topic',
      'line-block (translation required)': 'line-block',
      'parsed-literal (translation required)': 'parsed-literal',
      '醒目': 'rubric',
      '铭文': 'epigraph',
      '要点': 'highlights',
      'pull-quote (translation required)': 'pull-quote',
      '复合': 'compound',
      '容器': 'container',
      #u'questions (translation required)': 'questions',
      '表格': 'table',
      'csv表格': 'csv-table',
      '列表表格': 'list-table',
      #u'qa (translation required)': 'questions',
      #u'faq (translation required)': 'questions',
      '元数据': 'meta',
      'math (translation required)': 'math',
      #u'imagemap (translation required)': 'imagemap',
      '图片': 'image',
      '图例': 'figure',
      '包含': 'include',
      '原文': 'raw',
      '代替': 'replace',
      '统一码': 'unicode',
      '日期': 'date',
      '类型': 'class',
      '角色': 'role',
      '默认角色': 'default-role',
      '标题': 'title',
      '目录': 'contents',
      '章节序号': 'sectnum',
      '题头': 'header',
      '页脚': 'footer',
      #u'footnotes (translation required)': 'footnotes',
      #u'citations (translation required)': 'citations',
      'target-notes (translation required)': 'target-notes',
      'restructuredtext-test-directive': 'restructuredtext-test-directive'}
"""Simplified Chinese name to registered (in directives/__init__.py)
directive name mapping."""

roles = {
    # language-dependent: fixed
    '缩写': 'abbreviation',
    '简称': 'acronym',
    'code (translation required)': 'code',
    'index (translation required)': 'index',
    'i (translation required)': 'index',
    '下标': 'subscript',
    '上标': 'superscript',
    'title-reference (translation required)': 'title-reference',
    'title (translation required)': 'title-reference',
    't (translation required)': 'title-reference',
    'pep-reference (translation required)': 'pep-reference',
    'pep (translation required)': 'pep-reference',
    'rfc-reference (translation required)': 'rfc-reference',
    'rfc (translation required)': 'rfc-reference',
    '强调': 'emphasis',
    '加粗': 'strong',
    '字面': 'literal',
    'math (translation required)': 'math',
    'named-reference (translation required)': 'named-reference',
    'anonymous-reference (translation required)': 'anonymous-reference',
    'footnote-reference (translation required)': 'footnote-reference',
    'citation-reference (translation required)': 'citation-reference',
    'substitution-reference (translation required)': 'substitution-reference',
    'target (translation required)': 'target',
    'uri-reference (translation required)': 'uri-reference',
    'uri (translation required)': 'uri-reference',
    'url (translation required)': 'uri-reference',
    'raw (translation required)': 'raw',}
"""Mapping of Simplified Chinese role names to canonical role names
for interpreted text."""
