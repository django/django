# $Id: fa.py 4564 2016-08-10 11:48:42Z
# Author: Shahin <me@5hah.in>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Persian-language mappings for language-dependent features of
reStructuredText.
"""

__docformat__ = 'reStructuredText'


directives = {
    # language-dependent: fixed
    'توجه': 'attention',
    'احتیاط': 'caution',
    'کد': 'code',
    'بلوک-کد': 'code',
    'کد-منبع': 'code',
    'خطر': 'danger',
    'خطا': 'error',
    'راهنما': 'hint',
    'مهم': 'important',
    'یادداشت': 'note',
    'نکته': 'tip',
    'اخطار': 'warning',
    'تذکر': 'admonition',
    'نوار-کناری': 'sidebar',
    'موضوع': 'topic',
    'بلوک-خط': 'line-block',
    'تلفظ-پردازش-شده': 'parsed-literal',
    'سر-فصل': 'rubric',
    'کتیبه': 'epigraph',
    'نکات-برجسته': 'highlights',
    'نقل-قول': 'pull-quote',
    'ترکیب': 'compound',
    'ظرف': 'container',
    # 'questions': 'questions',
    'جدول': 'table',
    'جدول-csv': 'csv-table',
    'جدول-لیست': 'list-table',
    # 'qa': 'questions',
    # 'faq': 'questions',
    'متا': 'meta',
    'ریاضی': 'math',
    # 'imagemap': 'imagemap',
    'تصویر': 'image',
    'شکل': 'figure',
    'شامل': 'include',
    'خام': 'raw',
    'جایگزین': 'replace',
    'یونیکد': 'unicode',
    'تاریخ': 'date',
    'کلاس': 'class',
    'قانون': 'role',
    'قانون-پیش‌فرض': 'default-role',
    'عنوان': 'title',
    'محتوا': 'contents',
    'شماره-فصل': 'sectnum',
    'شماره‌گذاری-فصل': 'sectnum',
    'سرآیند': 'header',
    'پاصفحه': 'footer',
    # 'footnotes': 'footnotes',
    # 'citations': 'citations',
    'یادداشت-هدف': 'target-notes',
}
"""Persian name to registered (in directives/__init__.py) directive name
mapping."""

roles = {
    # language-dependent: fixed
    'مخفف': 'abbreviation',
    'سرنام': 'acronym',
    'کد': 'code',
    'شاخص': 'index',
    'زیرنویس': 'subscript',
    'بالانویس': 'superscript',
    'عنوان': 'title-reference',
    'نیرو': 'pep-reference',
    'rfc-reference (translation required)': 'rfc-reference',
    'تاکید': 'emphasis',
    'قوی': 'strong',
    'لفظی': 'literal',
    'ریاضی': 'math',
    'منبع-نام‌گذاری': 'named-reference',
    'منبع-ناشناس': 'anonymous-reference',
    'منبع-پانویس': 'footnote-reference',
    'منبع-نقل‌فول': 'citation-reference',
    'منبع-جایگزینی': 'substitution-reference',
    'هدف': 'target',
    'منبع-uri': 'uri-reference',
    'uri': 'uri-reference',
    'url': 'uri-reference',
    'خام': 'raw',
}
"""Mapping of Persian role names to canonical role names for interpreted text.
"""
