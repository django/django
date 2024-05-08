# $Id: ka.py 9444 2023-08-23 12:02:41Z grubert $
# Author: Temuri Doghonadze <temuri dot doghonadze at gmail dot com>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Georgian-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      'abstract': 'ანოტაცია',
      'address': 'მისამართი',
      'attention': 'ყურადღება!',
      'author': 'ავტორი',
      'authors': 'ავტორები',
      'caution': 'ფრთხილად!',
      'contact': 'კონტაქტი',
      'contents': 'შემცველობა',
      'copyright': 'საავტორო უფლებები',
      'danger': 'საშიშია!',
      'date': 'თარიღი',
      'dedication': 'მიძღვნა',
      'error': 'შეცდომა',
      'hint': 'რჩევა',
      'important': 'მნიშვნელოვანია',
      'note': 'შენიშვნა',
      'organization': 'ორგანიზაცია',
      'revision': 'რევიზია',
      'status': 'სტატუსი',
      'tip': 'მინიშნება',
      'version': 'ვერსია',
      'warning': 'გაფრთხილება'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      'ანოტაცია': 'abstract',
      'მისამართი': 'address',
      'ავტორი': 'author',
      'ავტორები': 'authors',
      'კონტაქტი': 'contact',
      'საავტორო უფლებები': 'copyright',
      'თარიღი': 'date',
      'მიძღვნა': 'dedication',
      'ორგანიზაცია': 'organization',
      'რევიზია': 'revision',
      'სტატუსი': 'status',
      'ვერსია': 'version'}
"""Georgian (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
