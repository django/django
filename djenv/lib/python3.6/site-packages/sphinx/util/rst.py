# -*- coding: utf-8 -*-
"""
    sphinx.util.rst
    ~~~~~~~~~~~~~~~

    reST helper functions.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import absolute_import

import re
from contextlib import contextmanager

from docutils.parsers.rst import roles
from docutils.parsers.rst.languages import en as english
from docutils.utils import Reporter

from sphinx.locale import __
from sphinx.util import logging

if False:
    # For type annotation
    from typing import Generator  # NOQA

symbols_re = re.compile(r'([!-\-/:-@\[-`{-~])')  # symbols without dot(0x2e)
logger = logging.getLogger(__name__)


def escape(text):
    # type: (unicode) -> unicode
    text = symbols_re.sub(r'\\\1', text)
    text = re.sub(r'^\.', r'\.', text)  # escape a dot at top
    return text


@contextmanager
def default_role(docname, name):
    # type: (unicode, unicode) -> Generator
    if name:
        dummy_reporter = Reporter('', 4, 4)
        role_fn, _ = roles.role(name, english, 0, dummy_reporter)
        if role_fn:
            roles._roles[''] = role_fn
        else:
            logger.warning(__('default role %s not found'), name, location=docname)

    yield

    roles._roles.pop('', None)  # if a document has set a local default role
