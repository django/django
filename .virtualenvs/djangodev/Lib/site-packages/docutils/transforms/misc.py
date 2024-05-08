# $Id: misc.py 9037 2022-03-05 23:31:10Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Miscellaneous transforms.
"""

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

    def apply(self):
        pending = self.startnode
        pending.details['callback'](pending)
        pending.parent.remove(pending)


class ClassAttribute(Transform):

    """
    Move the "class" attribute specified in the "pending" node into the
    immediately following non-comment element.
    """

    default_priority = 210

    def apply(self):
        pending = self.startnode
        parent = pending.parent
        child = pending
        while parent:
            # Check for appropriate following siblings:
            for index in range(parent.index(child) + 1, len(parent)):
                element = parent[index]
                if (isinstance(element, nodes.Invisible)
                    or isinstance(element, nodes.system_message)):
                    continue
                element['classes'] += pending.details['class']
                pending.parent.remove(pending)
                return
            else:
                # At end of section or container; apply to sibling
                child = parent
                parent = parent.parent
        error = self.document.reporter.error(
            'No suitable element following "%s" directive'
            % pending.details['directive'],
            nodes.literal_block(pending.rawsource, pending.rawsource),
            line=pending.line)
        pending.replace_self(error)


class Transitions(Transform):

    """
    Move transitions at the end of sections up the tree.  Complain
    on transitions after a title, at the beginning or end of the
    document, and after another transition.

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

    def apply(self):
        for node in self.document.findall(nodes.transition):
            self.visit_transition(node)

    def visit_transition(self, node):
        index = node.parent.index(node)
        error = None
        if (index == 0
            or isinstance(node.parent[0], nodes.title)
            and (index == 1
                 or isinstance(node.parent[1], nodes.subtitle)
                 and index == 2)):
            assert (isinstance(node.parent, nodes.document)
                    or isinstance(node.parent, nodes.section))
            error = self.document.reporter.error(
                'Document or section may not begin with a transition.',
                source=node.source, line=node.line)
        elif isinstance(node.parent[index - 1], nodes.transition):
            error = self.document.reporter.error(
                'At least one body element must separate transitions; '
                'adjacent transitions are not allowed.',
                source=node.source, line=node.line)
        if error:
            # Insert before node and update index.
            node.parent.insert(index, error)
            index += 1
        assert index < len(node.parent)
        if index != len(node.parent) - 1:
            # No need to move the node.
            return
        # Node behind which the transition is to be moved.
        sibling = node
        # While sibling is the last node of its parent.
        while index == len(sibling.parent) - 1:
            sibling = sibling.parent
            # If sibling is the whole document (i.e. it has no parent).
            if sibling.parent is None:
                # Transition at the end of document.  Do not move the
                # transition up, and place an error behind.
                error = self.document.reporter.error(
                    'Document may not end with a transition.',
                    line=node.line)
                node.parent.insert(node.parent.index(node) + 1, error)
                return
            index = sibling.parent.index(sibling)
        # Remove the original transition node.
        node.parent.remove(node)
        # Insert the transition after the sibling.
        sibling.parent.insert(index + 1, node)
