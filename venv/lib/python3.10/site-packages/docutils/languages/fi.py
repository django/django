# $Id: fi.py 9030 2022-03-05 23:28:32Z milde $
# Author: Asko Soukka <asko.soukka@iki.fi>
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <https://docutils.sourceforge.io/docs/howto/i18n.html>.
# Two files must be translated for each language: one in docutils/languages,
# the other in docutils/parsers/rst/languages.

"""
Finnish-language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': 'Tekij\u00e4',
      'authors': 'Tekij\u00e4t',
      'organization': 'Yhteis\u00f6',
      'address': 'Osoite',
      'contact': 'Yhteystiedot',
      'version': 'Versio',
      'revision': 'Vedos',
      'status': 'Tila',
      'date': 'P\u00e4iv\u00e4ys',
      'copyright': 'Tekij\u00e4noikeudet',
      'dedication': 'Omistuskirjoitus',
      'abstract': 'Tiivistelm\u00e4',
      'attention': 'Huomio!',
      'caution': 'Varo!',
      'danger': '!VAARA!',
      'error': 'Virhe',
      'hint': 'Vihje',
      'important': 'T\u00e4rke\u00e4\u00e4',
      'note': 'Huomautus',
      'tip': 'Neuvo',
      'warning': 'Varoitus',
      'contents': 'Sis\u00e4llys'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'tekij\u00e4': 'author',
      'tekij\u00e4t': 'authors',
      'yhteis\u00f6': 'organization',
      'osoite': 'address',
      'yhteystiedot': 'contact',
      'versio': 'version',
      'vedos': 'revision',
      'tila': 'status',
      'p\u00e4iv\u00e4ys': 'date',
      'tekij\u00e4noikeudet': 'copyright',
      'omistuskirjoitus': 'dedication',
      'tiivistelm\u00e4': 'abstract'}
"""Finnish (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
