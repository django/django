# -*- coding: utf-8 -*-
# $Id: ja.py 7119 2011-09-02 13:00:23Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Japanese-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'

# Corrections to these translations are welcome!
# 間違いがあれば、どうぞ正しい翻訳を教えて下さい。

directives = {
    # language-dependent: fixed
    '注目': 'attention',
    '注意': 'caution',
    'code (translation required)': 'code',
    '危険': 'danger',
    'エラー': 'error',
    'ヒント': 'hint',
    '重要': 'important',
    '備考': 'note',
    '通報': 'tip',
    '警告': 'warning',
    '戒告': 'admonition',
    'サイドバー': 'sidebar',
    'トピック': 'topic',
    'ラインブロック': 'line-block',
    'パーズドリテラル': 'parsed-literal',
    'ルブリック': 'rubric',
    'エピグラフ': 'epigraph',
    '題言': 'epigraph',
    'ハイライト': 'highlights',
    '見所': 'highlights',
    'プルクオート': 'pull-quote',
    '合成': 'compound',
    'コンテナー': 'container',
    '容器': 'container',
    '表': 'table',
    'csv表': 'csv-table',
    'リスト表': 'list-table',
    #u'質問': 'questions',
    #u'問答': 'questions',
    #u'faq': 'questions',
    'math (translation required)': 'math',
    'メタ': 'meta',
    #u'イメージマプ': 'imagemap',
    'イメージ': 'image',
    '画像': 'image',
    'フィグア': 'figure',
    '図版': 'figure',
    'インクルード': 'include',
    '含む': 'include',
    '組み込み': 'include',
    '生': 'raw',
    '原': 'raw',
    '換える': 'replace',
    '取り換える': 'replace',
    '掛け替える': 'replace',
    'ユニコード': 'unicode',
    '日付': 'date',
    'クラス': 'class',
    'ロール': 'role',
    '役': 'role',
    'ディフォルトロール': 'default-role',
    '既定役': 'default-role',
    'タイトル': 'title',
    '題': 'title',                    # 題名　件名
    '目次': 'contents',
    '節数': 'sectnum',
    'ヘッダ': 'header',
    'フッタ': 'footer',
    #u'脚注': 'footnotes',             # 脚註?
    #u'サイテーション': 'citations',　　　# 出典　引証　引用
    'ターゲットノート': 'target-notes', # 的注　的脚注
    }
"""Japanese name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    '略': 'abbreviation',
    '頭字語': 'acronym',
    'code (translation required)': 'code',
    'インデックス': 'index',
    '索引': 'index',
    '添字': 'subscript',
    '下付': 'subscript',
    '下': 'subscript',
    '上付': 'superscript',
    '上': 'superscript',
    '題参照': 'title-reference',
    'pep参照': 'pep-reference',
    'rfc参照': 'rfc-reference',
    '強調': 'emphasis',
    '強い': 'strong',
    'リテラル': 'literal',
    '整形済み': 'literal',
    'math (translation required)': 'math',
    '名付参照': 'named-reference',
    '無名参照': 'anonymous-reference',
    '脚注参照': 'footnote-reference',
    '出典参照': 'citation-reference',
    '代入参照': 'substitution-reference',
    '的': 'target',
    'uri参照': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    '生': 'raw',}
"""Mapping of Japanese role names to canonical role names for interpreted
text."""
