# $Id: fa.py 4564 2016-08-10 11:48:42Z
# Author: Shahin <me@5hah.in>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Arabic-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'

directives = {
    # language-dependent: fixed
    'تنبيه': 'attention',
    'احتیاط': 'caution',
    'كود': 'code',
    'خطر': 'danger',
    'خطأ': 'error',
    'تلميح': 'hint',
    'مهم': 'important',
    'ملاحظة': 'note',
    'نصيحة': 'tip',
    'تحذير': 'warning',
    'تذكير': 'admonition',
    'شريط-جانبي': 'sidebar',
    'موضوع': 'topic',
    'قالب-سطري': 'line-block',
    'لفظ-حرفي': 'parsed-literal',
    'معيار': 'rubric',
    'فكرة-الكتاب': 'epigraph',
    'تمييز': 'highlights',
    'نقل-قول': 'pull-quote',
    'ترکیب': 'compound',
    'وعاء': 'container',
    # 'questions': 'questions',
    'جدول': 'table',
    'جدول-csv': 'csv-table',
    'جدول-قوائم': 'list-table',
    # 'qa': 'questions',
    # 'faq': 'questions',
    'ميتا': 'meta',
    'رياضيات': 'math',
    # 'imagemap': 'imagemap',
    'صورة': 'image',
    'رسم-توضيحي': 'figure',
    'تضمين': 'include',
    'خام': 'raw',
    'تبديل': 'replace',
    'یونیکد': 'unicode',
    'تاریخ': 'date',
    'كائن': 'class',
    'قانون': 'role',
    'قانون-افتراضي': 'default-role',
    'عنوان': 'title',
    'المحتوى': 'contents',
    'رقم-الفصل': 'sectnum',
    'رقم-القسم': 'sectnum',
    'رأس-الصفحة': 'header',
    'هامش': 'footer',
    # 'footnotes': 'footnotes',
    # 'citations': 'citations',
    '': 'target-notes',
}
"""Arabic name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'اختصار': 'abbreviation',
    'اختزال': 'acronym',
    'كود': 'code',
    'فهرس': 'index',
    'خفض': 'subscript',
    'رفع': 'superscript',
    'عنوان-مرجع': 'title-reference',
    'مرجع-pep': 'pep-reference',
    'rfc-مرجع': 'rfc-reference',
    'تأكيد': 'emphasis',
    'عريض': 'strong',
    'لفظی': 'literal',
    'رياضيات': 'math',
    'مرجع-مسمى': 'named-reference',
    'مرجع-مجهول': 'anonymous-reference',
    'مرجع-هامشي': 'footnote-reference',
    'مرجع-منقول': 'citation-reference',
    'مرجع-معوض': 'substitution-reference',
    'هدف': 'target',
    'منبع-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'خام': 'raw',
}
"""Mapping of Arabic role names to canonical role names for interpreted text.
"""
