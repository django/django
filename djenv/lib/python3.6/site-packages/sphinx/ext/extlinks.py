# -*- coding: utf-8 -*-
"""
    sphinx.ext.extlinks
    ~~~~~~~~~~~~~~~~~~~

    Extension to save typing and prevent hard-coding of base URLs in the reST
    files.

    This adds a new config value called ``extlinks`` that is created like this::

       extlinks = {'exmpl': ('https://example.invalid/%s.html', prefix), ...}

    Now you can use e.g. :exmpl:`foo` in your documents.  This will create a
    link to ``https://example.invalid/foo.html``.  The link caption depends on
    the *prefix* value given:

    - If it is ``None``, the caption will be the full URL.
    - If it is a string (empty or not), the caption will be the prefix prepended
      to the role content.

    You can also give an explicit caption, e.g. :exmpl:`Foo <foo>`.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes, utils
from six import iteritems

import sphinx
from sphinx.util.nodes import split_explicit_title

if False:
    # For type annotation
    from typing import Any, Dict, List, Tuple  # NOQA
    from docutils.parsers.rst.states import Inliner  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.util.typing import RoleFunction  # NOQA


def make_link_role(base_url, prefix):
    # type: (unicode, unicode) -> RoleFunction
    def role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
        # type: (unicode, unicode, unicode, int, Inliner, Dict, List[unicode]) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
        text = utils.unescape(text)
        has_explicit_title, title, part = split_explicit_title(text)
        try:
            full_url = base_url % part
        except (TypeError, ValueError):
            inliner.reporter.warning(
                'unable to expand %s extlink with base URL %r, please make '
                'sure the base contains \'%%s\' exactly once'
                % (typ, base_url), line=lineno)
            full_url = base_url + part
        if not has_explicit_title:
            if prefix is None:
                title = full_url
            else:
                title = prefix + part
        pnode = nodes.reference(title, title, internal=False, refuri=full_url)
        return [pnode], []
    return role


def setup_link_roles(app):
    # type: (Sphinx) -> None
    for name, (base_url, prefix) in iteritems(app.config.extlinks):
        app.add_role(name, make_link_role(base_url, prefix))


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_config_value('extlinks', {}, 'env')
    app.connect('builder-inited', setup_link_roles)
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
