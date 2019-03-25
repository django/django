# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.errors
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Contains Error classes for the web support package.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""


class DocumentNotFoundError(Exception):
    pass


class UserNotAuthorizedError(Exception):
    pass


class CommentNotAllowedError(Exception):
    pass


class NullSearchException(Exception):
    pass
