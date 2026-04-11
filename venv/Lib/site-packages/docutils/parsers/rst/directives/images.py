# $Id: images.py 10102 2025-04-23 15:54:44Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Directives for figures and simple images.
"""

__docformat__ = 'reStructuredText'

from urllib.request import url2pathname

try:  # check for the Python Imaging Library
    import PIL.Image
except ImportError:
    try:  # sometimes PIL modules are put in PYTHONPATH's root
        import Image
        class PIL: pass  # noqa:E701  dummy wrapper
        PIL.Image = Image
    except ImportError:
        PIL = None

from docutils import nodes
from docutils.nodes import fully_normalize_name, whitespace_normalize_name
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives, states
from docutils.parsers.rst.roles import normalize_options


class Image(Directive):

    align_h_values = ('left', 'center', 'right')
    align_v_values = ('top', 'middle', 'bottom')
    align_values = align_v_values + align_h_values
    loading_values = ('embed', 'link', 'lazy')

    def align(argument):
        # This is not callable as `self.align()`.  We cannot make it a
        # staticmethod because we're saving an unbound method in
        # option_spec below.
        return directives.choice(argument, Image.align_values)

    def loading(argument):
        # This is not callable as `self.loading()` (see above).
        return directives.choice(argument, Image.loading_values)

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'alt': directives.unchanged,
                   'height': directives.length_or_unitless,
                   'width': directives.length_or_percentage_or_unitless,
                   'scale': directives.percentage,
                   'align': align,
                   'target': directives.unchanged_required,
                   'loading': loading,
                   'class': directives.class_option,
                   'name': directives.unchanged}

    def run(self):
        if 'align' in self.options:
            if isinstance(self.state, states.SubstitutionDef):
                # Check for align_v_values.
                if self.options['align'] not in self.align_v_values:
                    raise self.error(
                        'Error in "%s" directive: "%s" is not a valid value '
                        'for the "align" option within a substitution '
                        'definition.  Valid values for "align" are: "%s".'
                        % (self.name, self.options['align'],
                           '", "'.join(self.align_v_values)))
            elif self.options['align'] not in self.align_h_values:
                raise self.error(
                    'Error in "%s" directive: "%s" is not a valid value for '
                    'the "align" option.  Valid values for "align" are: "%s".'
                    % (self.name, self.options['align'],
                       '", "'.join(self.align_h_values)))
        messages = []
        reference = directives.uri(self.arguments[0])
        self.options['uri'] = reference
        reference_node = None
        if 'target' in self.options:
            block = states.escape2null(
                self.options['target']).splitlines()
            block = list(block)
            target_type, data = self.state.parse_target(
                block, self.block_text, self.lineno)
            if target_type == 'refuri':
                reference_node = nodes.reference(refuri=data)
            elif target_type == 'refname':
                reference_node = nodes.reference(
                    refname=fully_normalize_name(data),
                    name=whitespace_normalize_name(data))
                reference_node.indirect_reference_name = data
                self.state.document.note_refname(reference_node)
            else:                           # malformed target
                messages.append(data)       # data is a system message
            del self.options['target']
        options = normalize_options(self.options)
        image_node = nodes.image(self.block_text, **options)
        (image_node.source,
         image_node.line) = self.state_machine.get_source_and_line(self.lineno)
        self.add_name(image_node)
        if reference_node:
            reference_node += image_node
            return messages + [reference_node]
        else:
            return messages + [image_node]


class Figure(Image):

    def align(argument):
        return directives.choice(argument, Figure.align_h_values)

    def figwidth_value(argument):
        if argument.lower() == 'image':
            return 'image'
        else:
            return directives.length_or_percentage_or_unitless(argument, 'px')

    option_spec = Image.option_spec.copy()

    option_spec['figwidth'] = figwidth_value
    option_spec['figclass'] = directives.class_option
    option_spec['figname'] = directives.unchanged
    option_spec['align'] = align
    has_content = True

    def run(self):
        figwidth = self.options.pop('figwidth', None)
        figclasses = self.options.pop('figclass', None)
        figname = self.options.pop('figname', None)
        align = self.options.pop('align', None)
        (image_node,) = Image.run(self)
        if isinstance(image_node, nodes.system_message):
            return [image_node]
        figure_node = nodes.figure('', image_node)
        (figure_node.source, figure_node.line
         ) = self.state_machine.get_source_and_line(self.lineno)
        if figwidth == 'image':
            if PIL and self.state.document.settings.file_insertion_enabled:
                imagepath = url2pathname(image_node['uri'])
                try:
                    with PIL.Image.open(imagepath) as img:
                        figure_node['width'] = '%dpx' % img.size[0]
                except (OSError, UnicodeEncodeError):
                    pass  # TODO: warn/info?
                else:
                    self.state.document.settings.record_dependencies.add(
                        imagepath.replace('\\', '/'))
        elif figwidth is not None:
            figure_node['width'] = figwidth
        if figclasses:
            figure_node['classes'] += figclasses
        if figname:
            figure_node['names'].append(nodes.fully_normalize_name(figname))
            self.state.document.note_explicit_target(figure_node, figure_node)
        if align:
            figure_node['align'] = align
        if self.content:
            # optional caption (single paragraph or empty comment)
            # + optional legend (arbitrary body elements).
            node = nodes.Element()          # anonymous container for parsing
            self.state.nested_parse(self.content, self.content_offset, node)
            for i, child in enumerate(node):
                # skip temporary nodes that will be removed by transforms
                if isinstance(child, (nodes.target, nodes.pending)):
                    figure_node += child
                    continue
                if isinstance(child, nodes.paragraph):
                    caption = nodes.caption(child.rawsource, '',
                                            *child.children)
                    caption.source = child.source
                    caption.line = child.line
                    figure_node += caption
                    break
                if isinstance(child, nodes.comment) and len(child) == 0:
                    break
                error = self.reporter.error(
                    'Figure caption must be a paragraph or empty comment.',
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)
                return [figure_node, error]
            if len(node) > i+1:
                figure_node += nodes.legend('', *node[i+1:])
        return [figure_node]
