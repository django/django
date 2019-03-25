# $Id: admonitions.py 7681 2013-07-12 07:52:27Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Admonition directives.
"""

__docformat__ = 'reStructuredText'


from docutils.parsers.rst import Directive
from docutils.parsers.rst import states, directives
from docutils.parsers.rst.roles import set_classes
from docutils import nodes


class BaseAdmonition(Directive):

    final_argument_whitespace = True
    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged}
    has_content = True

    node_class = None
    """Subclasses must set this to the appropriate admonition node class."""

    def run(self):
        set_classes(self.options)
        self.assert_has_content()
        text = '\n'.join(self.content)
        admonition_node = self.node_class(text, **self.options)
        self.add_name(admonition_node)
        if self.node_class is nodes.admonition:
            title_text = self.arguments[0]
            textnodes, messages = self.state.inline_text(title_text,
                                                         self.lineno)
            title = nodes.title(title_text, '', *textnodes)
            title.source, title.line = (
                    self.state_machine.get_source_and_line(self.lineno))
            admonition_node += title
            admonition_node += messages
            if not 'classes' in self.options:
                admonition_node['classes'] += ['admonition-' +
                                               nodes.make_id(title_text)]
        self.state.nested_parse(self.content, self.content_offset,
                                admonition_node)
        return [admonition_node]


class Admonition(BaseAdmonition):

    required_arguments = 1
    node_class = nodes.admonition


class Attention(BaseAdmonition):

    node_class = nodes.attention


class Caution(BaseAdmonition):

    node_class = nodes.caution


class Danger(BaseAdmonition):

    node_class = nodes.danger


class Error(BaseAdmonition):

    node_class = nodes.error


class Hint(BaseAdmonition):

    node_class = nodes.hint


class Important(BaseAdmonition):

    node_class = nodes.important


class Note(BaseAdmonition):

    node_class = nodes.note


class Tip(BaseAdmonition):

    node_class = nodes.tip


class Warning(BaseAdmonition):

    node_class = nodes.warning
