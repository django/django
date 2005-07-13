"Wrapper for loading templates from storage of some sort (e.g. files or db)"
import template
from template_file import load_template_source

class ExtendsError(Exception):
    pass

def get_template(template_name):
    """
    Returns a compiled template.Template object for the given template name,
    handling template inheritance recursively.
    """
    return get_template_from_string(load_template_source(template_name))

def get_template_from_string(source):
    """
    Returns a compiled template.Template object for the given template code,
    handling template inheritance recursively.
    """
    return template.Template(source)

def select_template(template_name_list):
    "Given a list of template names, returns the first that can be loaded."
    for template_name in template_name_list:
        try:
            return get_template(template_name)
        except template.TemplateDoesNotExist:
            continue
    # If we get here, none of the templates could be loaded
    raise template.TemplateDoesNotExist, ', '.join(template_name_list)

class SuperBlock:
    "This implements the ability for {{ block.super }} to render the parent block's contents"
    def __init__(self, context, nodelist):
        self.context, self.nodelist = context, nodelist

    def super(self):
        if self.nodelist:
            return self.nodelist.render(self.context)
        else:
            return ''

class BlockNode(template.Node):
    def __init__(self, name, nodelist):
        self.name, self.nodelist = name, nodelist

    def __repr__(self):
        return "<Block Node: %s. Contents: %r>" % (self.name, self.nodelist)

    def render(self, context):
        context.push()
        nodelist = hasattr(self, 'original_node_list') and self.original_node_list or None
        context['block'] = SuperBlock(context, nodelist)
        result = self.nodelist.render(context)
        context.pop()
        return result

class ExtendsNode(template.Node):
    def __init__(self, nodelist, parent_name, parent_name_var, template_dirs=None):
        self.nodelist = nodelist
        self.parent_name, self.parent_name_var = parent_name, parent_name_var
        self.template_dirs = template_dirs

    def get_parent(self, context):
        if self.parent_name_var:
            self.parent_name = template.resolve_variable_with_filters(self.parent_name_var, context)
        parent = self.parent_name
        if not parent:
            error_msg = "Invalid template name in 'extends' tag: %r." % parent
            if self.parent_name_var:
                error_msg += " Got this from the %r variable." % self.parent_name_var
            raise template.TemplateSyntaxError, error_msg
        try:
            return get_template_from_string(load_template_source(parent, self.template_dirs))
        except template.TemplateDoesNotExist:
            raise template.TemplateSyntaxError, "Template %r cannot be extended, because it doesn't exist" % parent

    def render(self, context):
        compiled_parent = self.get_parent(context)
        parent_is_child = isinstance(compiled_parent.nodelist[0], ExtendsNode)
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
                if parent_is_child:
                    compiled_parent.nodelist[0].nodelist.append(block_node)
            else:
                # Save the original nodelist. It's used by BlockNode.
                parent_block.original_node_list = parent_block.nodelist
                parent_block.nodelist = block_node.nodelist
        return compiled_parent.render(context)

def do_block(parser, token):
    """
    Define a block that can be overridden by child templates.
    """
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "'%s' tag takes only one argument" % bits[0]
    block_name = bits[1]
    # Keep track of the names of BlockNodes found in this template, so we can
    # check for duplication.
    try:
        if block_name in parser.__loaded_blocks:
            raise template.TemplateSyntaxError, "'%s' tag with name '%s' appears more than once" % (bits[0], block_name)
        parser.__loaded_blocks.append(block_name)
    except AttributeError: # parser._loaded_blocks isn't a list yet
        parser.__loaded_blocks = [block_name]
    nodelist = parser.parse(('endblock',))
    parser.delete_first_token()
    return BlockNode(block_name, nodelist)

def do_extends(parser, token):
    """
    Signal that this template extends a parent template.
    
    This tag may be used in two ways: ``{% extends "base" %}`` (with quotes) 
    uses the literal value "base" as the name of the parent template to extend,
    or ``{% entends variable %}`` uses the value of ``variable`` as the name
    of the parent template to extend.
    """
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "'%s' takes one argument" % bits[0]
    parent_name, parent_name_var = None, None
    if (bits[1].startswith('"') and bits[1].endswith('"')) or (bits[1].startswith("'") and bits[1].endswith("'")):
        parent_name = bits[1][1:-1]
    else:
        parent_name_var = bits[1]
    nodelist = parser.parse()
    if nodelist.get_nodes_by_type(ExtendsNode):
        raise template.TemplateSyntaxError, "'%s' cannot appear more than once in the same template" % bits[0]
    return ExtendsNode(nodelist, parent_name, parent_name_var)

template.register_tag('block', do_block)
template.register_tag('extends', do_extends)
