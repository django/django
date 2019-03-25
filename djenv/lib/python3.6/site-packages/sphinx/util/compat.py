# -*- coding: utf-8 -*-
"""
    sphinx.util.compat
    ~~~~~~~~~~~~~~~~~~

    modules for backward compatibility

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from __future__ import absolute_import

import sys
import warnings

from six import string_types, iteritems

from sphinx.deprecation import RemovedInSphinx30Warning
from sphinx.util import import_object

if False:
    # For type annotation
    from typing import Any, Dict  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.config import Config  # NOQA


def deprecate_source_parsers(app, config):
    # type: (Sphinx, Config) -> None
    if config.source_parsers:
        warnings.warn('The config variable "source_parsers" is deprecated. '
                      'Please use app.add_source_parser() API instead.',
                      RemovedInSphinx30Warning)
        for suffix, parser in iteritems(config.source_parsers):
            if isinstance(parser, string_types):
                parser = import_object(parser, 'source parser')  # type: ignore
            app.add_source_parser(suffix, parser)


def register_application_for_autosummary(app):
    # type: (Sphinx) -> None
    """Register application object to autosummary module.

    Since Sphinx-1.7, documenters and attrgetters are registered into
    applicaiton object.  As a result, the arguments of
    ``get_documenter()`` has been changed.  To keep compatibility,
    this handler registers application object to the module.
    """
    if 'sphinx.ext.autosummary' in sys.modules:
        from sphinx.ext import autosummary
        autosummary._app = app


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.connect('config-inited', deprecate_source_parsers)
    app.connect('builder-inited', register_application_for_autosummary)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
