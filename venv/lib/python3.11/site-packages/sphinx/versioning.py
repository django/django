"""Implements the low-level algorithms Sphinx uses for versioning doctrees."""
from __future__ import annotations

import pickle
from itertools import product, zip_longest
from operator import itemgetter
from os import path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sphinx.transforms import SphinxTransform

if TYPE_CHECKING:
    from collections.abc import Iterator

    from docutils.nodes import Node

    from sphinx.application import Sphinx

try:
    import Levenshtein
    IS_SPEEDUP = True
except ImportError:
    IS_SPEEDUP = False

# anything below that ratio is considered equal/changed
VERSIONING_RATIO = 65


def add_uids(doctree: Node, condition: Any) -> Iterator[Node]:
    """Add a unique id to every node in the `doctree` which matches the
    condition and yield the nodes.

    :param doctree:
        A :class:`docutils.nodes.document` instance.

    :param condition:
        A callable which returns either ``True`` or ``False`` for a given node.
    """
    for node in doctree.findall(condition):
        node.uid = uuid4().hex
        yield node


def merge_doctrees(old: Node, new: Node, condition: Any) -> Iterator[Node]:
    """Merge the `old` doctree with the `new` one while looking at nodes
    matching the `condition`.

    Each node which replaces another one or has been added to the `new` doctree
    will be yielded.

    :param condition:
        A callable which returns either ``True`` or ``False`` for a given node.
    """
    old_iter = old.findall(condition)
    new_iter = new.findall(condition)
    old_nodes = []
    new_nodes = []
    ratios = {}
    seen = set()
    # compare the nodes each doctree in order
    for old_node, new_node in zip_longest(old_iter, new_iter):
        if old_node is None:
            new_nodes.append(new_node)
            continue
        if not getattr(old_node, 'uid', None):
            # maybe config.gettext_uuid has been changed.
            old_node.uid = uuid4().hex
        if new_node is None:
            old_nodes.append(old_node)
            continue
        ratio = get_ratio(old_node.rawsource, new_node.rawsource)
        if ratio == 0:
            new_node.uid = old_node.uid
            seen.add(new_node)
        else:
            ratios[old_node, new_node] = ratio
            old_nodes.append(old_node)
            new_nodes.append(new_node)
    # calculate the ratios for each unequal pair of nodes, should we stumble
    # on a pair which is equal we set the uid and add it to the seen ones
    for old_node, new_node in product(old_nodes, new_nodes):
        if new_node in seen or (old_node, new_node) in ratios:
            continue
        ratio = get_ratio(old_node.rawsource, new_node.rawsource)
        if ratio == 0:
            new_node.uid = old_node.uid
            seen.add(new_node)
        else:
            ratios[old_node, new_node] = ratio
    # choose the old node with the best ratio for each new node and set the uid
    # as long as the ratio is under a certain value, in which case we consider
    # them not changed but different
    ratios = sorted(ratios.items(), key=itemgetter(1))  # type: ignore[assignment]
    for (old_node, new_node), ratio in ratios:
        if new_node in seen:
            continue
        else:
            seen.add(new_node)
        if ratio < VERSIONING_RATIO:
            new_node.uid = old_node.uid
        else:
            new_node.uid = uuid4().hex
            yield new_node
    # create new uuids for any new node we left out earlier, this happens
    # if one or more nodes are simply added.
    for new_node in set(new_nodes) - seen:
        new_node.uid = uuid4().hex
        yield new_node


def get_ratio(old: str, new: str) -> float:
    """Return a "similarity ratio" (in percent) representing the similarity
    between the two strings where 0 is equal and anything above less than equal.
    """
    if not all([old, new]):
        return VERSIONING_RATIO

    if IS_SPEEDUP:
        return Levenshtein.distance(old, new) / (len(old) / 100.0)
    else:
        return levenshtein_distance(old, new) / (len(old) / 100.0)


def levenshtein_distance(a: str, b: str) -> int:
    """Return the Levenshtein edit distance between two strings *a* and *b*."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not a:
        return len(b)
    previous_row = list(range(len(b) + 1))
    for i, column1 in enumerate(a):
        current_row = [i + 1]
        for j, column2 in enumerate(b):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (column1 != column2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


class UIDTransform(SphinxTransform):
    """Add UIDs to doctree for versioning."""
    default_priority = 880

    def apply(self, **kwargs: Any) -> None:
        env = self.env
        old_doctree = None
        if not env.versioning_condition:
            return

        if env.versioning_compare:
            # get old doctree
            try:
                filename = path.join(env.doctreedir, env.docname + '.doctree')
                with open(filename, 'rb') as f:
                    old_doctree = pickle.load(f)
            except OSError:
                pass

        # add uids for versioning
        if not env.versioning_compare or old_doctree is None:
            list(add_uids(self.document, env.versioning_condition))
        else:
            list(merge_doctrees(old_doctree, self.document, env.versioning_condition))


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_transform(UIDTransform)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
