# Author: Meir Kriheli
# Id: $Id: he.py 9452 2023-09-27 00:11:54Z milde $
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Hebrew-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
    # fixed: language-dependent
    'author': 'מחבר',
    'authors': 'מחברי',
    'organization': 'ארגון',
    'address': 'כתובת',
    'contact': 'איש קשר',
    'version': 'גרסה',
    'revision': 'מהדורה',
    'status': 'סטטוס',
    'date': 'תאריך',
    'copyright': 'זכויות שמורות',
    'dedication': 'הקדשה',
    'abstract': 'תקציר',
    'attention': 'תשומת לב',
    'caution': 'זהירות',
    'danger': 'סכנה',
    'error': 'שגיאה',
    'hint': 'רמז',
    'important': 'חשוב',
    'note': 'הערה',
    'tip': 'טיפ',
    'warning': 'אזהרה',
    'contents': 'תוכן',
    }
"""Mapping of node class name to label text."""

bibliographic_fields = {
    # language-dependent: fixed
    'מחבר': 'author',
    'מחברי': 'authors',
    'ארגון': 'organization',
    'כתובת': 'address',
    'איש קשר': 'contact',
    'גרסה': 'version',
    'מהדורה': 'revision',
    'סטטוס': 'status',
    'תאריך': 'date',
    'זכויות שמורות': 'copyright',
    'הקדשה': 'dedication',
    'תקציר': 'abstract',
    }
"""Hebrew to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
