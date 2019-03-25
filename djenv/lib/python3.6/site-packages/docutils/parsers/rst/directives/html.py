# $Id: html.py 7320 2012-01-19 22:33:02Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Directives for typically HTML-specific constructs.
"""

__docformat__ = 'reStructuredText'

import sys
from docutils import nodes, utils
from docutils.parsers.rst import Directive
from docutils.parsers.rst import states
from docutils.transforms import components


class MetaBody(states.SpecializedBody):

    class meta(nodes.Special, nodes.PreBibliographic, nodes.Element):
        """HTML-specific "meta" element."""
        pass

    def field_marker(self, match, context, next_state):
        """Meta element."""
        node, blank_finish = self.parsemeta(match)
        self.parent += node
        return [], next_state, []

    def parsemeta(self, match):
        name = self.parse_field_marker(match)
        indented, indent, line_offset, blank_finish = \
              self.state_machine.get_first_known_indented(match.end())
        node = self.meta()
        pending = nodes.pending(components.Filter,
                                {'component': 'writer',
                                 'format': 'html',
                                 'nodes': [node]})
        node['content'] = ' '.join(indented)
        if not indented:
            line = self.state_machine.line
            msg = self.reporter.info(
                  'No content for meta tag "%s".' % name,
                  nodes.literal_block(line, line))
            return msg, blank_finish
        tokens = name.split()
        try:
            attname, val = utils.extract_name_value(tokens[0])[0]
            node[attname.lower()] = val
        except utils.NameValueError:
            node['name'] = tokens[0]
        for token in tokens[1:]:
            try:
                attname, val = utils.extract_name_value(token)[0]
                node[attname.lower()] = val
            except utils.NameValueError as detail:
                line = self.state_machine.line
                msg = self.reporter.error(
                      'Error parsing meta tag attribute "%s": %s.'
                      % (token, detail), nodes.literal_block(line, line))
                return msg, blank_finish
        self.document.note_pending(pending)
        return pending, blank_finish


class Meta(Directive):

    has_content = True

    SMkwargs = {'state_classes': (MetaBody,)}

    def run(self):
        self.assert_has_content()
        node = nodes.Element()
        new_line_offset, blank_finish = self.state.nested_list_parse(
            self.content, self.content_offset, node,
            initial_state='MetaBody', blank_finish=True,
            state_machine_kwargs=self.SMkwargs)
        if (new_line_offset - self.content_offset) != len(self.content):
            # incomplete parse of block?
            error = self.state_machine.reporter.error(
                'Invalid meta directive.',
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
            node += error
        return node.children
