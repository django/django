# $Id: body.py 10263 2025-11-28 13:51:32Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Directives for additional body elements.

See `docutils.parsers.rst.directives` for API details.
"""

__docformat__ = 'reStructuredText'


from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives
from docutils.parsers.rst.roles import normalize_options
from docutils.utils.code_analyzer import Lexer, LexerError, NumberLines


class BasePseudoSection(Directive):
    """Base class for Topic and Sidebar."""

    final_argument_whitespace = True
    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged}
    has_content = True

    node_class = None
    """Node class to be used (must be set in subclasses)."""

    invalid_parents = (nodes.SubStructural, nodes.Bibliographic,
                       nodes.Decorative, nodes.Body, nodes.Part, nodes.topic)
    """
    Node categories where topics and sidebars are invalid children.

    Sidebars are only valid in <document> and <section> elements,
    topics also in <sidebar> elements. However, during parsing,
    there may be wrapper nodes (like `sphinx.addnodes.only`).
    """

    def run(self):
        if (not isinstance(self.state_machine.node,
                           (nodes.Root, nodes.section, nodes.sidebar))
            and isinstance(self.state_machine.node, self.invalid_parents)):
            raise self.error('The "%s" directive may not be used within '
                             'topics or body elements.' % self.name)
        self.assert_has_content()
        if self.arguments:  # title (in sidebars optional)
            title_text = self.arguments[0]
            textnodes, messages = self.state.inline_text(
                                      title_text, self.lineno)
            titles = [nodes.title(title_text, '', *textnodes)]
            # Sidebar uses this code.
            if 'subtitle' in self.options:
                textnodes, more_messages = self.state.inline_text(
                    self.options['subtitle'], self.lineno)
                titles.append(nodes.subtitle(self.options['subtitle'], '',
                                             *textnodes))
                messages.extend(more_messages)
        else:
            titles = []
            messages = []
        text = '\n'.join(self.content)
        node = self.node_class(text, *(titles + messages))
        node['classes'] += self.options.get('class', [])
        (node.source,
         node.line) = self.state_machine.get_source_and_line(self.lineno)
        self.add_name(node)
        if text:
            self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


class Topic(BasePseudoSection):

    required_arguments = 1
    node_class = nodes.topic


class Sidebar(BasePseudoSection):

    optional_arguments = 1
    node_class = nodes.sidebar
    option_spec = BasePseudoSection.option_spec | {
                      'subtitle': directives.unchanged_required}

    def run(self):
        if isinstance(self.state_machine.node, nodes.sidebar):
            raise self.error('The "%s" directive may not be used within a '
                             'sidebar element.' % self.name)
        if 'subtitle' in self.options and not self.arguments:
            raise self.error('The "subtitle" option may not be used '
                             'without a title.')

        return BasePseudoSection.run(self)


class LineBlock(Directive):
    """Legacy directive for line blocks.

    Use is deprecated in favour of the line block syntax,
    cf. `parsers.rst.states.Body.line_block()`.
    """

    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged}
    has_content = True

    def run(self):
        self.assert_has_content()
        block = nodes.line_block(classes=self.options.get('class', []))
        (block.source,
         block.line) = self.state_machine.get_source_and_line(self.lineno)
        self.add_name(block)
        node_list = [block]
        for i, line_text in enumerate(self.content):
            text_nodes, messages = self.state.inline_text(
                line_text.strip(), self.lineno + self.content_offset)
            line = nodes.line(line_text, '', *text_nodes)
            line.source = block.source
            line.line = block.line + i
            if line_text.strip():
                line.indent = len(line_text) - len(line_text.lstrip())
            block += line
            node_list.extend(messages)
            self.content_offset += 1
        self.state.nest_line_block_lines(block)
        return node_list


class ParsedLiteral(Directive):

    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged}
    has_content = True

    def run(self):
        options = normalize_options(self.options)
        self.assert_has_content()
        text = '\n'.join(self.content)
        text_nodes, messages = self.state.inline_text(text, self.lineno)
        node = nodes.literal_block(text, '', *text_nodes, **options)
        node.line = self.content_offset + 1
        self.add_name(node)
        return [node] + messages


class CodeBlock(Directive):
    """Parse and mark up content of a code block.

    Configuration setting: syntax_highlight
       Highlight Code content with Pygments?
       Possible values: ('long', 'short', 'none')

    """
    optional_arguments = 1
    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged,
                   'number-lines': directives.unchanged  # integer or None
                   }
    has_content = True

    def run(self):
        self.assert_has_content()
        if self.arguments:
            language = self.arguments[0]
        else:
            language = ''
        options = normalize_options(self.options)
        classes = ['code']
        if language:
            classes.append(language)
        if 'classes' in options:
            classes.extend(options['classes'])

        # set up lexical analyzer
        try:
            tokens = Lexer('\n'.join(self.content), language,
                           self.state.document.settings.syntax_highlight)
        except LexerError as error:
            if self.state.document.settings.report_level > 2:
                # don't report warnings -> insert without syntax highlight
                tokens = Lexer('\n'.join(self.content), language, 'none')
            else:
                raise self.warning(error)

        if 'number-lines' in options:
            # optional argument `startline`, defaults to 1
            try:
                startline = int(options['number-lines'] or 1)
            except ValueError:
                raise self.error(':number-lines: with non-integer start value')
            endline = startline + len(self.content)
            # add linenumber filter:
            tokens = NumberLines(tokens, startline, endline)

        node = nodes.literal_block('\n'.join(self.content), classes=classes)
        self.add_name(node)
        # if called from "include", set the source
        if 'source' in options:
            node.attributes['source'] = options['source']
        # analyze content and add nodes for every token
        for classes, value in tokens:
            if classes:
                node += nodes.inline(value, value, classes=classes)
            else:
                # insert as Text to decrease the verbosity of the output
                node += nodes.Text(value)

        return [node]


class MathBlock(Directive):

    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged,
                   # TODO: Add Sphinx' ``mathbase.py`` option 'nowrap'?
                   # 'nowrap': directives.flag,
                   }
    has_content = True

    def run(self):
        options = normalize_options(self.options)
        self.assert_has_content()
        # join lines, separate blocks
        content = '\n'.join(self.content).split('\n\n')
        _nodes = []
        for block in content:
            if not block:
                continue
            node = nodes.math_block(self.block_text, block, **options)
            (node.source,
             node.line) = self.state_machine.get_source_and_line(self.lineno)
            self.add_name(node)
            _nodes.append(node)
        return _nodes


class Rubric(Directive):

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged}

    def run(self):
        options = normalize_options(self.options)
        rubric_text = self.arguments[0]
        textnodes, messages = self.state.inline_text(rubric_text, self.lineno)
        rubric = nodes.rubric(rubric_text, '', *textnodes, **options)
        self.add_name(rubric)
        return [rubric] + messages


class BlockQuote(Directive):

    has_content = True
    classes = []

    def run(self):
        self.assert_has_content()
        elements = self.state.block_quote(self.content, self.content_offset)
        for element in elements:
            if isinstance(element, nodes.block_quote):
                element['classes'] += self.classes
        return elements


class Epigraph(BlockQuote):

    classes = ['epigraph']


class Highlights(BlockQuote):

    classes = ['highlights']


class PullQuote(BlockQuote):

    classes = ['pull-quote']


class Compound(Directive):

    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged}
    has_content = True

    def run(self):
        self.assert_has_content()
        text = '\n'.join(self.content)
        node = nodes.compound(text)
        node['classes'] += self.options.get('class', [])
        (node.source,
         node.line) = self.state_machine.get_source_and_line(self.lineno)
        self.add_name(node)
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


class Container(Directive):

    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {'name': directives.unchanged}
    has_content = True

    def run(self):
        self.assert_has_content()
        text = '\n'.join(self.content)
        try:
            if self.arguments:
                classes = directives.class_option(self.arguments[0])
            else:
                classes = []
        except ValueError:
            raise self.error(
                'Invalid class attribute value for "%s" directive: "%s".'
                % (self.name, self.arguments[0]))
        node = nodes.container(text)
        node['classes'].extend(classes)
        (node.source,
         node.line) = self.state_machine.get_source_and_line(self.lineno)
        self.add_name(node)
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]
