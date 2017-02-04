import logging
import posixpath
import warnings
from collections import defaultdict

from django.utils.deprecation import RemovedInDjango21Warning
from django.utils.safestring import mark_safe

from .base import (
    Node, Template, TemplateSyntaxError, TextNode, Variable, token_kwargs,
)
from .library import Library

register = Library()

BLOCK_CONTEXT_KEY = 'block_context'

logger = logging.getLogger('django.template')


class BlockContext:
    def __init__(self):
        # Dictionary of FIFO queues.
        self.blocks = defaultdict(list)

    def add_blocks(self, blocks):
        for name, block in blocks.items():
            self.blocks[name].insert(0, block)

    def pop(self, name):
        try:
            return self.blocks[name].pop()
        except IndexError:
            return None

    def push(self, name, block):
        self.blocks[name].append(block)

    def get_block(self, name):
        try:
            return self.blocks[name][-1]
        except IndexError:
            return None


class BlockNode(Node):
    def __init__(self, name, nodelist, parent=None):
        self.name, self.nodelist, self.parent = name, nodelist, parent

    def __repr__(self):
        return "<Block Node: %s. Contents: %r>" % (self.name, self.nodelist)

    def render(self, context):
        block_context = context.render_context.get(BLOCK_CONTEXT_KEY)
        with context.push():
            if block_context is None:
                context['block'] = self
                result = self.nodelist.render(context)
            else:
                push = block = block_context.pop(self.name)
                if block is None:
                    block = self
                # Create new block so we can store context without thread-safety issues.
                block = type(self)(block.name, block.nodelist)
                block.context = context
                context['block'] = block
                result = block.nodelist.render(context)
                if push is not None:
                    block_context.push(self.name, push)
        return result

    def super(self):
        if not hasattr(self, 'context'):
            raise TemplateSyntaxError(
                "'%s' object has no attribute 'context'. Did you use "
                "{{ block.super }} in a base template?" % self.__class__.__name__
            )
        render_context = self.context.render_context
        if (BLOCK_CONTEXT_KEY in render_context and
                render_context[BLOCK_CONTEXT_KEY].get_block(self.name) is not None):
            return mark_safe(self.render(self.context))
        return ''


class ExtendsNode(Node):
    must_be_first = True
    context_key = 'extends_context'

    def __init__(self, nodelist, parent_name, template_dirs=None):
        self.nodelist = nodelist
        self.parent_name = parent_name
        self.template_dirs = template_dirs
        self.blocks = {n.name: n for n in nodelist.get_nodes_by_type(BlockNode)}

    def __repr__(self):
        return '<%s: extends %s>' % (self.__class__.__name__, self.parent_name.token)

    def find_template(self, template_name, context):
        """
        This is a wrapper around engine.find_template(). A history is kept in
        the render_context attribute between successive extends calls and
        passed as the skip argument. This enables extends to work recursively
        without extending the same template twice.
        """
        history = context.render_context.setdefault(
            self.context_key, [context.template.origin],
        )
        template, origin = context.template.engine.find_template(
            template_name, skip=history,
        )
        history.append(origin)
        return template

    def get_parent(self, context):
        parent = self.parent_name.resolve(context)
        if not parent:
            error_msg = "Invalid template name in 'extends' tag: %r." % parent
            if self.parent_name.filters or\
                    isinstance(self.parent_name.var, Variable):
                error_msg += " Got this from the '%s' variable." %\
                    self.parent_name.token
            raise TemplateSyntaxError(error_msg)
        if isinstance(parent, Template):
            # parent is a django.template.Template
            return parent
        if isinstance(getattr(parent, 'template', None), Template):
            # parent is a django.template.backends.django.Template
            return parent.template
        return self.find_template(parent, context)

    def render(self, context):
        compiled_parent = self.get_parent(context)

        if BLOCK_CONTEXT_KEY not in context.render_context:
            context.render_context[BLOCK_CONTEXT_KEY] = BlockContext()
        block_context = context.render_context[BLOCK_CONTEXT_KEY]

        # Add the block nodes from this node to the block context
        block_context.add_blocks(self.blocks)

        # If this block's parent doesn't have an extends node it is the root,
        # and its block nodes also need to be added to the block context.
        for node in compiled_parent.nodelist:
            # The ExtendsNode has to be the first non-text node.
            if not isinstance(node, TextNode):
                if not isinstance(node, ExtendsNode):
                    blocks = {n.name: n for n in
                              compiled_parent.nodelist.get_nodes_by_type(BlockNode)}
                    block_context.add_blocks(blocks)
                break

        # Call Template._render explicitly so the parser context stays
        # the same.
        return compiled_parent._render(context)


class IncludeNode(Node):
    context_key = '__include_context'

    def __init__(self, template, *args, extra_context=None, isolated_context=False, **kwargs):
        self.template = template
        self.extra_context = extra_context or {}
        self.isolated_context = isolated_context
        super().__init__(*args, **kwargs)

    def render(self, context):
        """
        Render the specified template and context. Cache the template object
        in render_context to avoid reparsing and loading when used in a for
        loop.
        """
        try:
            template = self.template.resolve(context)
            # Does this quack like a Template?
            if not callable(getattr(template, 'render', None)):
                # If not, we'll try our cache, and get_template()
                template_name = template
                cache = context.render_context.setdefault(self.context_key, {})
                template = cache.get(template_name)
                if template is None:
                    template = context.template.engine.get_template(template_name)
                    cache[template_name] = template
            values = {
                name: var.resolve(context)
                for name, var in self.extra_context.items()
            }
            if self.isolated_context:
                return template.render(context.new(values))
            with context.push(**values):
                return template.render(context)
        except Exception as e:
            if context.template.engine.debug:
                raise
            template_name = getattr(context, 'template_name', None) or 'unknown'
            warnings.warn(
                "Rendering {%% include '%s' %%} raised %s. In Django 2.1, "
                "this exception will be raised rather than silenced and "
                "rendered as an empty string." %
                (template_name, e.__class__.__name__),
                RemovedInDjango21Warning,
            )
            logger.warning(
                "Exception raised while rendering {%% include %%} for "
                "template '%s'. Empty string rendered instead.",
                template_name,
                exc_info=True,
            )
            return ''


@register.tag('block')
def do_block(parser, token):
    """
    Define a block that can be overridden by child templates.
    """
    # token.split_contents() isn't useful here because this tag doesn't accept variable as arguments
    bits = token.contents.split()
    if len(bits) != 2:
        raise TemplateSyntaxError("'%s' tag takes only one argument" % bits[0])
    block_name = bits[1]
    # Keep track of the names of BlockNodes found in this template, so we can
    # check for duplication.
    try:
        if block_name in parser.__loaded_blocks:
            raise TemplateSyntaxError("'%s' tag with name '%s' appears more than once" % (bits[0], block_name))
        parser.__loaded_blocks.append(block_name)
    except AttributeError:  # parser.__loaded_blocks isn't a list yet
        parser.__loaded_blocks = [block_name]
    nodelist = parser.parse(('endblock',))

    # This check is kept for backwards-compatibility. See #3100.
    endblock = parser.next_token()
    acceptable_endblocks = ('endblock', 'endblock %s' % block_name)
    if endblock.contents not in acceptable_endblocks:
        parser.invalid_block_tag(endblock, 'endblock', acceptable_endblocks)

    return BlockNode(block_name, nodelist)


def construct_relative_path(current_template_name, relative_name):
    """
    Convert a relative path (starting with './' or '../') to the full template
    name based on the current_template_name.
    """
    if not any(relative_name.startswith(x) for x in ["'./", "'../", '"./', '"../']):
        # relative_name is a variable or a literal that doesn't contain a
        # relative path.
        return relative_name

    new_name = posixpath.normpath(
        posixpath.join(
            posixpath.dirname(current_template_name.lstrip('/')),
            relative_name.strip('\'"')
        )
    )
    if new_name.startswith('../'):
        raise TemplateSyntaxError(
            "The relative path '%s' points outside the file hierarchy that "
            "template '%s' is in." % (relative_name, current_template_name)
        )
    if current_template_name.lstrip('/') == new_name:
        raise TemplateSyntaxError(
            "The relative path '%s' was translated to template name '%s', the "
            "same template in which the tag appears."
            % (relative_name, current_template_name)
        )
    return '"%s"' % new_name


@register.tag('extends')
def do_extends(parser, token):
    """
    Signal that this template extends a parent template.

    This tag may be used in two ways: ``{% extends "base" %}`` (with quotes)
    uses the literal value "base" as the name of the parent template to extend,
    or ``{% extends variable %}`` uses the value of ``variable`` as either the
    name of the parent template to extend (if it evaluates to a string) or as
    the parent template itself (if it evaluates to a Template object).
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("'%s' takes one argument" % bits[0])
    bits[1] = construct_relative_path(parser.origin.template_name, bits[1])
    parent_name = parser.compile_filter(bits[1])
    nodelist = parser.parse()
    if nodelist.get_nodes_by_type(ExtendsNode):
        raise TemplateSyntaxError("'%s' cannot appear more than once in the same template" % bits[0])
    return ExtendsNode(nodelist, parent_name)


@register.tag('include')
def do_include(parser, token):
    """
    Loads a template and renders it with the current context. You can pass
    additional context using keyword arguments.

    Example::

        {% include "foo/some_include" %}
        {% include "foo/some_include" with bar="BAZZ!" baz="BING!" %}

    Use the ``only`` argument to exclude the current context when rendering
    the included template::

        {% include "foo/some_include" only %}
        {% include "foo/some_include" with bar="1" only %}
    """
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError(
            "%r tag takes at least one argument: the name of the template to "
            "be included." % bits[0]
        )
    options = {}
    remaining_bits = bits[2:]
    while remaining_bits:
        option = remaining_bits.pop(0)
        if option in options:
            raise TemplateSyntaxError('The %r option was specified more '
                                      'than once.' % option)
        if option == 'with':
            value = token_kwargs(remaining_bits, parser, support_legacy=False)
            if not value:
                raise TemplateSyntaxError('"with" in %r tag needs at least '
                                          'one keyword argument.' % bits[0])
        elif option == 'only':
            value = True
        else:
            raise TemplateSyntaxError('Unknown argument for %r tag: %r.' %
                                      (bits[0], option))
        options[option] = value
    isolated_context = options.get('only', False)
    namemap = options.get('with', {})
    bits[1] = construct_relative_path(parser.origin.template_name, bits[1])
    return IncludeNode(parser.compile_filter(bits[1]), extra_context=namemap,
                       isolated_context=isolated_context)
