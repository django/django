"""Add external links to module code in Python object descriptions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes

import sphinx
from sphinx import addnodes
from sphinx.errors import SphinxError
from sphinx.locale import _

if TYPE_CHECKING:
    from docutils.nodes import Node

    from sphinx.application import Sphinx


class LinkcodeError(SphinxError):
    category = "linkcode error"


def doctree_read(app: Sphinx, doctree: Node) -> None:
    env = app.builder.env

    resolve_target = getattr(env.config, 'linkcode_resolve', None)
    if not callable(env.config.linkcode_resolve):
        msg = 'Function `linkcode_resolve` is not given in conf.py'
        raise LinkcodeError(msg)
    assert resolve_target is not None  # for mypy

    domain_keys = {
        'py': ['module', 'fullname'],
        'c': ['names'],
        'cpp': ['names'],
        'js': ['object', 'fullname'],
    }

    for objnode in list(doctree.findall(addnodes.desc)):
        domain = objnode.get('domain')
        uris: set[str] = set()
        for signode in objnode:
            if not isinstance(signode, addnodes.desc_signature):
                continue

            # Convert signode to a specified format
            info = {}
            for key in domain_keys.get(domain, []):
                value = signode.get(key)
                if not value:
                    value = ''
                info[key] = value
            if not info:
                continue

            # Call user code to resolve the link
            uri = resolve_target(domain, info)
            if not uri:
                # no source
                continue

            if uri in uris or not uri:
                # only one link per name, please
                continue
            uris.add(uri)

            inline = nodes.inline('', _('[source]'), classes=['viewcode-link'])
            onlynode = addnodes.only(expr='html')
            onlynode += nodes.reference('', '', inline, internal=False, refuri=uri)
            signode += onlynode


def setup(app: Sphinx) -> dict[str, Any]:
    app.connect('doctree-read', doctree_read)
    app.add_config_value('linkcode_resolve', None, '')
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
