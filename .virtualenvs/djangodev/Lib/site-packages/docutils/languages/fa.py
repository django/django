# $Id: fa.py 4564 2016-08-10 11:48:42Z
# Author: Shahin <me@5hah.in>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Persian-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'نویسنده',
      'authors': 'نویسندگان',
      'organization': 'سازمان',
      'address': 'آدرس',
      'contact': 'تماس',
      'version': 'نسخه',
      'revision': 'بازبینی',
      'status': 'وضعیت',
      'date': 'تاریخ',
      'copyright': 'کپی‌رایت',
      'dedication': 'تخصیص',
      'abstract': 'چکیده',
      'attention': 'توجه!',
      'caution': 'احتیاط!',
      'danger': 'خطر!',
      'error': 'خطا',
      'hint': 'راهنما',
      'important': 'مهم',
      'note': 'یادداشت',
      'tip': 'نکته',
      'warning': 'اخطار',
      'contents': 'محتوا'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'نویسنده': 'author',
      'نویسندگان': 'authors',
      'سازمان': 'organization',
      'آدرس': 'address',
      'تماس': 'contact',
      'نسخه': 'version',
      'بازبینی': 'revision',
      'وضعیت': 'status',
      'تاریخ': 'date',
      'کپی‌رایت': 'copyright',
      'تخصیص': 'dedication',
      'چکیده': 'abstract'}
"""Persian (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = ['؛', '،']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
