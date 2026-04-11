# $Id: fa.py 4564 2016-08-10 11:48:42Z
# Author: Shahin <me@5hah.in>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Arabic-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'المؤلف',
      'authors': 'المؤلفون',
      'organization': 'التنظيم',
      'address': 'العنوان',
      'contact': 'اتصل',
      'version': 'نسخة',
      'revision': 'مراجعة',
      'status': 'الحالة',
      'date': 'تاریخ',
      'copyright': 'الحقوق',
      'dedication': 'إهداء',
      'abstract': 'ملخص',
      'attention': 'تنبيه',
      'caution': 'احتیاط',
      'danger': 'خطر',
      'error': 'خطأ',
      'hint': 'تلميح',
      'important': 'مهم',
      'note': 'ملاحظة',
      'tip': 'نصيحة',
      'warning': 'تحذير',
      'contents': 'المحتوى'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'مؤلف': 'author',
      'مؤلفون': 'authors',
      'التنظيم': 'organization',
      'العنوان': 'address',
      'اتصل': 'contact',
      'نسخة': 'version',
      'مراجعة': 'revision',
      'الحالة': 'status',
      'تاریخ': 'date',
      'الحقوق': 'copyright',
      'إهداء': 'dedication',
      'ملخص': 'abstract'}
"""Arabic (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = ['؛', '،']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
