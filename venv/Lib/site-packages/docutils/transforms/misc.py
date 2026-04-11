# $Id: misc.py 10265 2025-11-28 13:51:57Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Miscellaneous transforms.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

from docutils import nodes
from docutils.transforms import Transform


class CallBack(Transform):

    """
    Inserts a callback into a document.  The callback is called when the
    transform is applied, which is determined by its priority.

    For use with `nodes.pending` elements.  Requires a ``details['callback']``
    entry, a bound method or function which takes one parameter: the pending
    node.  Other data can be stored in the ``details`` attribute or in the
    object hosting the callback method.
    """

    default_priority = 990

    def apply(self) -> None:
        pending = self.startnode
        pending.details['callback'](pending)
        pending.parent.remove(pending)


class ClassAttribute(Transform):

    """
    Move the "class" attribute specified in the "pending" node into the
    next visible element.
    """

    default_priority = 210

    def apply(self) -> None:
        pending = self.startnode
        for element in pending.findall(include_self=False, descend=False,
                                       siblings=True, ascend=True):
            if isinstance(element, (nodes.Invisible, nodes.system_message)):
                continue
            element['classes'] += pending.details['class']
            pending.parent.remove(pending)
            return

        error = self.document.reporter.error(
            'No suitable element following "%s" directive'
            % pending.details['directive'],
            nodes.literal_block(pending.rawsource, pending.rawsource),
            line=pending.line)
        pending.replace_self(error)


class Transitions(Transform):

    """
    Move transitions at the end of sections up the tree.  Complain
    on transitions after a title, subtitle, meta, or decoration element,
    at the beginning or end of the document, and after another transition.

    For example, transform this::

        <section>
            ...
            <transition>
        <section>
            ...

    into this::

        <section>
            ...
        <transition>
        <section>
            ...
    """

    default_priority = 830

    def apply(self) -> None:
        for node in self.document.findall(nodes.transition):
            self.visit_transition(node)

    def visit_transition(self, node) -> None:
        index = node.parent.index(node)
        previous_sibling = node.previous_sibling()
        msg = ''
        if not isinstance(node.parent, (nodes.document, nodes.section)):
            msg = 'Transition must be child of <document> or <section>.'
        elif index == 0 or isinstance(previous_sibling, (nodes.title,
                                                         nodes.subtitle,
                                                         nodes.meta,
                                                         nodes.decoration)):
            msg = 'Document or section may not begin with a transition.'
        elif isinstance(previous_sibling, nodes.transition):
            msg = ('At least one body element must separate transitions; '
                   'adjacent transitions are not allowed.')
        if msg:
            warning = self.document.reporter.warning(msg, base_node=node)
            # Check, if it is valid to insert a body element
            node.parent[index] = nodes.paragraph()
            try:
                node.parent.validate(recursive=False)
            except nodes.ValidationError:
                node.parent[index] = node
            else:
                node.parent[index] = node
                node.parent.insert(index+1, warning)
                index += 1
        if not isinstance(node.parent, (nodes.document, nodes.section)):
            return
        assert index < len(node.parent)
        if index != len(node.parent) - 1:
            # No need to move the node.
            return
        # Node behind which the transition is to be moved.
        sibling = node
        # While sibling is the last node of its parent.
        while index == len(sibling.parent) - 1:
            sibling = sibling.parent
            if sibling.parent is None:  # sibling is the top node (document)
                # Transition at the end of document.  Do not move the
                # transition up, and place a warning behind.
                warning = self.document.reporter.warning(
                              'Document may not end with a transition.',
                              base_node=node)
                node.parent.append(warning)
                return
            index = sibling.parent.index(sibling)
        # Remove the original transition node.
        node.parent.remove(node)
        # Insert the transition after the sibling.
        sibling.parent.insert(index + 1, node)
