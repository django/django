"""Transforms for HTML builder."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from docutils import nodes

from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util.nodes import NodeMatcher

if TYPE_CHECKING:
    from sphinx.application import Sphinx


class KeyboardTransform(SphinxPostTransform):
    """Transform :kbd: role to more detailed form.

    Before::

        <literal class="kbd">
            Control-x

    After::

        <literal class="kbd compound">
            <literal class="kbd">
                Control
            -
            <literal class="kbd">
                x
    """
    default_priority = 400
    formats = ('html',)
    pattern = re.compile(r'(?<=.)(-|\+|\^|\s+)(?=.)')
    multiwords_keys = (('caps', 'lock'),
                       ('page', 'down'),
                       ('page', 'up'),
                       ('scroll', 'lock'),
                       ('num', 'lock'),
                       ('sys', 'rq'),
                       ('back', 'space'))

    def run(self, **kwargs: Any) -> None:
        matcher = NodeMatcher(nodes.literal, classes=["kbd"])
        # this list must be pre-created as during iteration new nodes
        # are added which match the condition in the NodeMatcher.
        for node in list(self.document.findall(matcher)):  # type: nodes.literal
            parts = self.pattern.split(node[-1].astext())
            if len(parts) == 1 or self.is_multiwords_key(parts):
                continue

            node['classes'].append('compound')
            node.pop()
            while parts:
                if self.is_multiwords_key(parts):
                    key = ''.join(parts[:3])
                    parts[:3] = []
                else:
                    key = parts.pop(0)
                node += nodes.literal('', key, classes=["kbd"])

                try:
                    # key separator (ex. -, +, ^)
                    sep = parts.pop(0)
                    node += nodes.Text(sep)
                except IndexError:
                    pass

    def is_multiwords_key(self, parts: list[str]) -> bool:
        if len(parts) >= 3 and parts[1].strip() == '':
            name = parts[0].lower(), parts[2].lower()
            return name in self.multiwords_keys
        else:
            return False


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_post_transform(KeyboardTransform)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
