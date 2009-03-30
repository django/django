from django.template import TemplateSyntaxError, TemplateDoesNotExist, Variable
from django.template import Library, Node, TextNode
from django.template.loader import get_template, get_template_from_string, find_template_source
from django.conf import settings
from django.utils.safestring import mark_safe

register = Library()

class ExtendsError(Exception):
    pass

class BlockNode(Node):
    def __init__(self, name, nodelist, parent=None):
        self.name, self.nodelist, self.parent = name, nodelist, parent

    def __repr__(self):
        return "<Block Node: %s. Contents: %r>" % (self.name, self.nodelist)

    def render(self, context):
        context.push()
        # Save context in case of block.super().
        self.context = context
        context['block'] = self
        result = self.nodelist.render(context)
        context.pop()
        return result

    def super(self):
        if self.parent:
            return mark_safe(self.parent.render(self.context))
        return ''

    def add_parent(self, nodelist):
        if self.parent:
            self.parent.add_parent(nodelist)
        else:
            self.parent = BlockNode(self.name, nodelist)

class ExtendsNode(Node):
    must_be_first = True

    def __init__(self, nodelist, parent_name, parent_name_expr, template_dirs=None):
        self.nodelist = nodelist
        self.parent_name, self.parent_name_expr = parent_name, parent_name_expr
        self.template_dirs = template_dirs

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
            source, origin = find_template_source(parent, self.template_dirs)
        except TemplateDoesNotExist:
            raise TemplateSyntaxError, "Template %r cannot be extended, because it doesn't exist" % parent
        else:
            return get_template_from_string(source, origin, parent)

    def render(self, context):
        compiled_parent = self.get_parent(context)
        parent_blocks = dict([(n.name, n) for n in compiled_parent.nodelist.get_nodes_by_type(BlockNode)])
        for block_node in self.nodelist.get_nodes_by_type(BlockNode):
            # Check for a BlockNode with this node's name, and replace it if found.
            try:
                parent_block = parent_blocks[block_node.name]
            except KeyError:
                # This BlockNode wasn't found in the parent template, but the
                # parent block might be defined in the parent's *parent*, so we
                # add this BlockNode to the parent's ExtendsNode nodelist, so
                # it'll be checked when the parent node's render() is called.

                # Find out if the parent template has a parent itself
                for node in compiled_parent.nodelist:
                    if not isinstance(node, TextNode):
                        # If the first non-text node is an extends, handle it.
                        if isinstance(node, ExtendsNode):
                            node.nodelist.append(block_node)
                        # Extends must be the first non-text node, so once you find
                        # the first non-text node you can stop looking. 
                        break
            else:
                # Keep any existing parents and add a new one. Used by BlockNode.
                parent_block.parent = block_node.parent
                parent_block.add_parent(parent_block.nodelist)
                parent_block.nodelist = block_node.nodelist
        return compiled_parent.render(context)

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
