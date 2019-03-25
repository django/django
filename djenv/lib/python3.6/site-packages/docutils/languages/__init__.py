# $Id: __init__.py 7648 2013-04-18 07:36:22Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

# Internationalization details are documented in
# <http://docutils.sf.net/docs/howto/i18n.html>.

"""
This package contains modules for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

import sys

from docutils.utils import normalize_language_tag
if sys.version_info < (2,5):
    from docutils._compat import __import__

_languages = {}

def get_language(language_code, reporter=None):
    """Return module with language localizations.

    `language_code` is a "BCP 47" language tag.
    If there is no matching module, warn and fall back to English.
    """
    # TODO: use a dummy module returning emtpy strings?, configurable?
    for tag in normalize_language_tag(language_code):
        tag = tag.replace('-','_') # '-' not valid in module names
        if tag in _languages:
            return _languages[tag]
        try:
            module = __import__(tag, globals(), locals(), level=1)
        except ImportError:
            try:
                module = __import__(tag, globals(), locals(), level=0)
            except ImportError:
                continue
        _languages[tag] = module
        return module
    if reporter is not None:
        reporter.warning(
            'language "%s" not supported: ' % language_code +
            'Docutils-generated text will be in English.')
    module = __import__('en', globals(), locals(), level=1)
    _languages[tag] = module # warn only one time!
    return module
