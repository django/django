from collections import defaultdict

from django.conf import settings
from django.template.base import TemplateSyntaxError, Library, Node, TextNode,\
    token_kwargs, Variable
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.utils import six

register = Library()

BLOCK_CONTEXT_KEY = 'block_context'

class ExtendsError(Exception):
    pass

class BlockContext(object):
    def __init__(self):
        # Dictionary of FIFO queues.
        self.blocks = defaultdict(list)

    def add_blocks(self, blocks):
        for name, block in six.iteritems(blocks):
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
        context.push()
        if block_context is None:
            context['block'] = self
            result = self.nodelist.render(context)
        else:
            push = block = block_context.pop(self.name)
            if block is None:
                block = self
            # Create new block so we can store context without thread-safety issues.
            block = BlockNode(block.name, block.nodelist)
            block.context = context
            context['block'] = block
            result = block.nodelist.render(context)
            if push is not None:
                block_context.push(self.name, push)
        context.pop()
        return result

    def super(self):
        render_context = self.context.render_context
        if (BLOCK_CONTEXT_KEY in render_context and
            render_context[BLOCK_CONTEXT_KEY].get_block(self.name) is not None):
            return mark_safe(self.render(self.context))
        return ''

class ExtendsNode(Node):
    must_be_first = True

    def __init__(self, nodelist, parent_name, template_dirs=None):
        self.nodelist = nodelist
        self.parent_name = parent_name
        self.template_dirs = template_dirs
        self.blocks = dict([(n.name, n) for n in nodelist.get_nodes_by_type(BlockNode)])

    def __repr__(self):
        return '<ExtendsNode: extends %s>' % self.parent_name.token

    def get_parent(self, context):
        parent = self.parent_name.resolve(context)
        if not parent:
            error_msg = "Invalid template name in 'extends' tag: %r." % parent
            if self.parent_name.filters or\
                    isinstance(self.parent_name.var, Variable):
                error_msg += " Got this from the '%s' variable." %\
                    self.parent_name.token
            raise TemplateSyntaxError(error_msg)
        if hasattr(parent, 'render'):
            return parent # parent is a Template object
        return get_template(parent)

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
                    blocks = dict([(n.name, n) for n in
                                   compiled_parent.nodelist.get_nodes_by_type(BlockNode)])
                    block_context.add_blocks(blocks)
                break

        # Call Template._render explicitly so the parser context stays
        # the same.
        return compiled_parent._render(context)

class BaseIncludeNode(Node):
    def __init__(self, *args, **kwargs):
        self.extra_context = kwargs.pop('extra_context', {})
        self.isolated_context = kwargs.pop('isolated_context', False)
        super(BaseIncludeNode, self).__init__(*args, **kwargs)

    def render_template(self, template, context):
        values = dict([(name, var.resolve(context)) for name, var
                       in six.iteritems(self.extra_context)])
        if self.isolated_context:
            return template.render(context.new(values))
        context.update(values)
        output = template.render(context)
        context.pop()
        return output

class ConstantIncludeNode(BaseIncludeNode):
    def __init__(self, template_path, *args, **kwargs):
        super(ConstantIncludeNode, self).__init__(*args, **kwargs)
        try:
            t = get_template(template_path)
            self.template = t
        except:
            if settings.TEMPLATE_DEBUG:
                raise
            self.template = None

    def render(self, context):
        if not self.template:
            return ''
        return self.render_template(self.template, context)

class IncludeNode(BaseIncludeNode):
    def __init__(self, template_name, *args, **kwargs):
        super(IncludeNode, self).__init__(*args, **kwargs)
        self.template_name = template_name

    def render(self, context):
        try:
            template_name = self.template_name.resolve(context)
            template = get_template(template_name)
            return self.render_template(template, context)
        except:
            if settings.TEMPLATE_DEBUG:
                raise
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
    except AttributeError: # parser.__loaded_blocks isn't a list yet
        parser.__loaded_blocks = [block_name]
    nodelist = parser.parse(('endblock',))

    # This check is kept for backwards-compatibility. See #3100.
    endblock = parser.next_token()
    acceptable_endblocks = ('endblock', 'endblock %s' % block_name)
    if endblock.contents not in acceptable_endblocks:
        parser.invalid_block_tag(endblock, 'endblock', acceptable_endblocks)

    return BlockNode(block_name, nodelist)

@register.tag('extends')
def do_extends(parser, token):
    """
    Signal that this template extends a parent template.

    This tag may be used in two ways: ``{% extends "base" %}`` (with quotes)
    uses the literal value "base" as the name of the parent template to extend,
    or ``{% extends variable %}`` uses the value of ``variable`` as either the
    name of the parent template to extend (if it evaluates to a string) or as
    the parent tempate itelf (if it evaluates to a Template object).
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("'%s' takes one argument" % bits[0])
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
        raise TemplateSyntaxError("%r tag takes at least one argument: the name of the template to be included." % bits[0])
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
    path = bits[1]
    if path[0] in ('"', "'") and path[-1] == path[0]:
        return ConstantIncludeNode(path[1:-1], extra_context=namemap,
                                   isolated_context=isolated_context)
    return IncludeNode(parser.compile_filter(bits[1]), extra_context=namemap,
                       isolated_context=isolated_context)
