# $Id: components.py 9037 2022-03-05 23:31:10Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Docutils component-related transforms.
"""

from docutils.transforms import Transform

__docformat__ = 'reStructuredText'


class Filter(Transform):

    """
    Include or exclude elements which depend on a specific Docutils component.

    For use with `nodes.pending` elements.  A "pending" element's dictionary
    attribute ``details`` must contain the keys "component" and "format".  The
    value of ``details['component']`` must match the type name of the
    component the elements depend on (e.g. "writer").  The value of
    ``details['format']`` is the name of a specific format or context of that
    component (e.g. "html").  If the matching Docutils component supports that
    format or context, the "pending" element is replaced by the contents of
    ``details['nodes']`` (a list of nodes); otherwise, the "pending" element
    is removed.

    For example, up to version 0.17, the reStructuredText "meta"
    directive created a "pending" element containing a "meta" element
    (in ``pending.details['nodes']``).
    Only writers (``pending.details['component'] == 'writer'``)
    supporting the "html", "latex", or "odf" formats
    (``pending.details['format'] == 'html,latex,odf'``) included the
    "meta" element; it was deleted from the output of all other writers.

    This transform is no longer used by Docutils, it may be removed in future.
    """
    # TODO: clean up or keep this for 3rd party (or possible future) use?
    # (GM 2021-05-18)

    default_priority = 780

    def apply(self):
        pending = self.startnode
        component_type = pending.details['component']  # 'reader' or 'writer'
        formats = (pending.details['format']).split(',')
        component = self.document.transformer.components[component_type]
        for format in formats:
            if component.supports(format):
                pending.replace_self(pending.details['nodes'])
                break
        else:
            pending.parent.remove(pending)
