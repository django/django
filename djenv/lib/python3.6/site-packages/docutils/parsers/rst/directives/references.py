# $Id: references.py 7062 2011-06-30 22:14:29Z milde $
# Authors: David Goodger <goodger@python.org>; Dmitry Jemerov
# Copyright: This module has been placed in the public domain.

"""
Directives for references and targets.
"""

__docformat__ = 'reStructuredText'

from docutils import nodes
from docutils.transforms import references
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives


class TargetNotes(Directive):

    """Target footnote generation."""

    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged}

    def run(self):
        pending = nodes.pending(references.TargetNotes)
        self.add_name(pending)
        pending.details.update(self.options)
        self.state_machine.document.note_pending(pending)
        return [pending]
