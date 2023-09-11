# $Id: __init__.py 9030 2022-03-05 23:28:32Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

# Internationalization details are documented in
# <https://docutils.sourceforge.io/docs/howto/i18n.html>.

"""
This package contains modules for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

from importlib import import_module

from docutils.utils import normalize_language_tag


class LanguageImporter:
    """Import language modules.

    When called with a BCP 47 language tag, instances return a module
    with localisations from `docutils.languages` or the PYTHONPATH.

    If there is no matching module, warn (if a `reporter` is passed)
    and fall back to English.
    """
    packages = ('docutils.languages.', '')
    warn_msg = ('Language "%s" not supported: '
                'Docutils-generated text will be in English.')
    fallback = 'en'
    # TODO: use a dummy module returning empty strings?, configurable?

    def __init__(self):
        self.cache = {}

    def import_from_packages(self, name, reporter=None):
        """Try loading module `name` from `self.packages`."""
        module = None
        for package in self.packages:
            try:
                module = import_module(package+name)
                self.check_content(module)
            except (ImportError, AttributeError):
                if reporter and module:
                    reporter.info(f'{module} is no complete '
                                  'Docutils language module.')
                elif reporter:
                    reporter.info(f'Module "{package+name}" not found.')
                continue
            break
        return module

    def check_content(self, module):
        """Check if we got a Docutils language module."""
        if not (isinstance(module.labels, dict)
                and isinstance(module.bibliographic_fields, dict)
                and isinstance(module.author_separators, list)):
            raise ImportError

    def __call__(self, language_code, reporter=None):
        try:
            return self.cache[language_code]
        except KeyError:
            pass
        for tag in normalize_language_tag(language_code):
            tag = tag.replace('-', '_')  # '-' not valid in module names
            module = self.import_from_packages(tag, reporter)
            if module is not None:
                break
        else:
            if reporter:
                reporter.warning(self.warn_msg % language_code)
            if self.fallback:
                module = self.import_from_packages(self.fallback)
        if reporter and (language_code != 'en'):
            reporter.info('Using %s for language "%s".'
                          % (module, language_code))
        self.cache[language_code] = module
        return module


get_language = LanguageImporter()
