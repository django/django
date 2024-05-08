# $Id: fi.py 9452 2023-09-27 00:11:54Z milde $
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
      'author': 'Tekijä',
      'authors': 'Tekijät',
      'organization': 'Yhteisö',
      'address': 'Osoite',
      'contact': 'Yhteystiedot',
      'version': 'Versio',
      'revision': 'Vedos',
      'status': 'Tila',
      'date': 'Päiväys',
      'copyright': 'Tekijänoikeudet',
      'dedication': 'Omistuskirjoitus',
      'abstract': 'Tiivistelmä',
      'attention': 'Huomio!',
      'caution': 'Varo!',
      'danger': '!VAARA!',
      'error': 'Virhe',
      'hint': 'Vihje',
      'important': 'Tärkeää',
      'note': 'Huomautus',
      'tip': 'Neuvo',
      'warning': 'Varoitus',
      'contents': 'Sisällys'}
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'tekijä': 'author',
      'tekijät': 'authors',
      'yhteisö': 'organization',
      'osoite': 'address',
      'yhteystiedot': 'contact',
      'versio': 'version',
      'vedos': 'revision',
      'tila': 'status',
      'päiväys': 'date',
      'tekijänoikeudet': 'copyright',
      'omistuskirjoitus': 'dedication',
      'tiivistelmä': 'abstract'}
"""Finnish (lowcased) to canonical name mapping for bibliographic fields."""

author_separators = [';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
