from django.template import TemplateSyntaxError, TemplateDoesNotExist, Variable
from django.template import Library, Node, TextNode
from django.template.loader import get_template
from django.conf import settings
from django.utils.safestring import mark_safe

register = Library()

BLOCK_CONTEXT_KEY = 'block_context'

class ExtendsError(Exception):
    pass

class BlockContext(object):
    def __init__(self):
        # Dictionary of FIFO queues.
        self.blocks = {}

    def add_blocks(self, blocks):
        for name, block in blocks.iteritems():
            if name in self.blocks:
                self.blocks[name].insert(0, block)
            else:
                self.blocks[name] = [block]

    def pop(self, name):
        try:
            return self.blocks[name].pop()
        except (IndexError, KeyError):
            return None

    def push(self, name, block):
        self.blocks[name].append(block)

    def get_block(self, name):
        try:
            return self.blocks[name][-1]
        except (IndexError, KeyError):
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

    def __init__(self, nodelist, parent_name, parent_name_expr, template_dirs=None):
        self.nodelist = nodelist
        self.parent_name, self.parent_name_expr = parent_name, parent_name_expr
        self.template_dirs = template_dirs
        self.blocks = dict([(n.name, n) for n in nodelist.get_nodes_by_type(BlockNode)])

    def __repr__(self):
        if self.parent_name_expr:
            return "<ExtendsNode: extends %s>" % self.parent_name_expr.token
        return '<ExtendsNode: extends "%s">' % self.parent_name

    def get_parent(self, context):
        if self.parent_name_expr:
            self.parent_name = self.parent_name_expr.resolve(context)
        parent = self.parent_name
        if not parent:
            error_msg = "Invalid template name in 'extends' tag: %r." % parent
            if self.parent_name_expr:
                error_msg += " Got this from the '%s' variable." % self.parent_name_expr.token
            raise TemplateSyntaxError, error_msg
        if hasattr(parent, 'render'):
            return parent # parent is a Template object
        try:
            return get_template(parent)
        except TemplateDoesNotExist:
            raise TemplateSyntaxError, "Template %r cannot be extended, because it doesn't exist" % parent

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

class ConstantIncludeNode(Node):
    def __init__(self, template_path):
        try:
            t = get_template(template_path)
            self.template = t
        except:
            if settings.TEMPLATE_DEBUG:
                raise
            self.template = None

    def render(self, context):
        if self.template:
            return self.template.render(context)
        else:
            return ''

class IncludeNode(Node):
    def __init__(self, template_name):
        self.template_name = Variable(template_name)

    def render(self, context):
        try:
            template_name = self.template_name.resolve(context)
            t = get_template(template_name)
            return t.render(context)
        except TemplateSyntaxError, e:
            if settings.TEMPLATE_DEBUG:
                raise
            return ''
        except:
            return '' # Fail silently for invalid included templates.

def do_block(parser, token):
    """
    Define a block that can be overridden by child templates.
    """
    bits = token.contents.split()
    if len(bits) != 2:
        raise TemplateSyntaxError, "'%s' tag takes only one argument" % bits[0]
    block_name = bits[1]
    # Keep track of the names of BlockNodes found in this template, so we can
    # check for duplication.
    try:
        if block_name in parser.__loaded_blocks:
            raise TemplateSyntaxError, "'%s' tag with name '%s' appears more than once" % (bits[0], block_name)
        parser.__loaded_blocks.append(block_name)
    except AttributeError: # parser.__loaded_blocks isn't a list yet
        parser.__loaded_blocks = [block_name]
    nodelist = parser.parse(('endblock', 'endblock %s' % block_name))
    parser.delete_first_token()
    return BlockNode(block_name, nodelist)

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
        raise TemplateSyntaxError, "'%s' takes one argument" % bits[0]
    parent_name, parent_name_expr = None, None
    if bits[1][0] in ('"', "'") and bits[1][-1] == bits[1][0]:
        parent_name = bits[1][1:-1]
    else:
        parent_name_expr = parser.compile_filter(bits[1])
    nodelist = parser.parse()
    if nodelist.get_nodes_by_type(ExtendsNode):
        raise TemplateSyntaxError, "'%s' cannot appear more than once in the same template" % bits[0]
    return ExtendsNode(nodelist, parent_name, parent_name_expr)

def do_include(parser, token):
    """
    Loads a template and renders it with the current context.

    Example::

        {% include "foo/some_include" %}
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError, "%r tag takes one argument: the name of the template to be included" % bits[0]
    path = bits[1]
    if path[0] in ('"', "'") and path[-1] == path[0]:
        return ConstantIncludeNode(path[1:-1])
    return IncludeNode(bits[1])

register.tag('block', do_block)
register.tag('extends', do_extends)
register.tag('include', do_include)
