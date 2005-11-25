# Wrapper for loading templates from storage of some sort (e.g. filesystem, database).
#
# This uses the TEMPLATE_LOADERS setting, which is a list of loaders to use.
# Each loader is expected to have this interface:
#
#    callable(name, dirs=[])
#
# name is the template name.
# dirs is an optional list of directories to search instead of TEMPLATE_DIRS.
#
# The loader should return a tuple of (template_source, path). The path returned
# might be shown to the user for debugging purposes, so it should identify where
# the template was loaded from.
#
# Each loader should have an "is_usable" attribute set. This is a boolean that
# specifies whether the loader can be used in this Python installation. Each
# loader is responsible for setting this when it's initialized.
#
# For example, the eggs loader (which is capable of loading templates from
# Python eggs) sets is_usable to False if the "pkg_resources" module isn't
# installed, because pkg_resources is necessary to read eggs.

from django.core.exceptions import ImproperlyConfigured
from django.core.template import Origin, StringOrigin, Template, Context, Node, TemplateDoesNotExist, TemplateSyntaxError, resolve_variable_with_filters, resolve_variable, register_tag
from django.conf.settings import TEMPLATE_LOADERS, TEMPLATE_DEBUG

template_source_loaders = []
for path in TEMPLATE_LOADERS:
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]
    try:
        mod = __import__(module, globals(), locals(), [attr])
    except ImportError, e:
        raise ImproperlyConfigured, 'Error importing template source loader %s: "%s"' % (module, e)
    try:
        func = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured, 'Module "%s" does not define a "%s" callable template source loader' % (module, attr)
    if not func.is_usable:
        import warnings
        warnings.warn("Your TEMPLATE_LOADERS setting includes %r, but your Python installation doesn't support that type of template loading. Consider removing that line from TEMPLATE_LOADERS." % path)
    else:
        template_source_loaders.append(func)

class LoaderOrigin(Origin):
    def __init__(self, display_name, loader, name, dirs):
        super(LoaderOrigin, self).__init__(display_name)
        self.loader, self.loadname, self.dirs = loader, name, dirs

    def reload(self):
        return self.loader(self.loadname, self.dirs)[0]

def make_origin(display_name, loader, name, dirs):
    if TEMPLATE_DEBUG:
        return LoaderOrigin(display_name, loader, name, dirs)
    else:
        return None

def find_template_source(name, dirs=None):
    for loader in template_source_loaders:
        try:
            source, display_name = loader(name, dirs)
            return (source, make_origin(display_name, loader, name, dirs))
        except TemplateDoesNotExist:
            pass
    raise TemplateDoesNotExist, name

def load_template_source(name, dirs=None):
    find_template_source(name, dirs)[0]

class ExtendsError(Exception):
    pass

def get_template(template_name):
    """
    Returns a compiled Template object for the given template name,
    handling template inheritance recursively.
    """
    return get_template_from_string(*find_template_source(template_name))

def get_template_from_string(source, origin=None ):
    """
    Returns a compiled Template object for the given template code,
    handling template inheritance recursively.
    """
    return Template(source, origin)

def render_to_string(template_name, dictionary=None, context_instance=None):
    """
    Loads the given template_name and renders it with the given dictionary as
    context. The template_name may be a string to load a single template using
    get_template, or it may be a tuple to use select_template to find one of
    the templates in the list. Returns a string.
    """
    dictionary = dictionary or {}
    if isinstance(template_name, (list, tuple)):
        t = select_template(template_name)
    else:
        t = get_template(template_name)
    if context_instance:
        context_instance.update(dictionary)
    else:
        context_instance = Context(dictionary)
    return t.render(context_instance)

def select_template(template_name_list):
    "Given a list of template names, returns the first that can be loaded."
    for template_name in template_name_list:
        try:
            return get_template(template_name)
        except TemplateDoesNotExist:
            continue
    # If we get here, none of the templates could be loaded
    raise TemplateDoesNotExist, ', '.join(template_name_list)

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
            return self.parent.render(self.context)
        return ''

    def add_parent(self, nodelist):
        if self.parent:
            self.parent.add_parent(nodelist)
        else:
            self.parent = BlockNode(self.name, nodelist)

class ExtendsNode(Node):
    def __init__(self, nodelist, parent_name, parent_name_var, template_dirs=None):
        self.nodelist = nodelist
        self.parent_name, self.parent_name_var = parent_name, parent_name_var
        self.template_dirs = template_dirs

    def get_parent(self, context):
        if self.parent_name_var:
            self.parent_name = resolve_variable_with_filters(self.parent_name_var, context)
        parent = self.parent_name
        if not parent:
            error_msg = "Invalid template name in 'extends' tag: %r." % parent
            if self.parent_name_var:
                error_msg += " Got this from the %r variable." % self.parent_name_var
            raise TemplateSyntaxError, error_msg
        try:
            return get_template_from_string(*find_template_source(parent, self.template_dirs))
        except TemplateDoesNotExist:
            raise TemplateSyntaxError, "Template %r cannot be extended, because it doesn't exist" % parent

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
        except Exception, e:
            if TEMPLATE_DEBUG:
                raise
            self.template = None

    def render(self, context):
        if self.template:
            return self.template.render(context)
        else:
            return ''

class IncludeNode(Node):
    def __init__(self, template_name):
        self.template_name = template_name

    def render(self, context):
         try:
             template_name = resolve_variable(self.template_name, context)
             t = get_template(template_name)
             return t.render(context)
         except TemplateSyntaxError, e:
             if TEMPLATE_DEBUG:
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
    or ``{% extends variable %}`` uses the value of ``variable`` as the name
    of the parent template to extend.
    """
    bits = token.contents.split()
    if len(bits) != 2:
        raise TemplateSyntaxError, "'%s' takes one argument" % bits[0]
    parent_name, parent_name_var = None, None
    if bits[1][0] in ('"', "'") and bits[1][-1] == bits[1][0]:
        parent_name = bits[1][1:-1]
    else:
        parent_name_var = bits[1]
    nodelist = parser.parse()
    if nodelist.get_nodes_by_type(ExtendsNode):
        raise TemplateSyntaxError, "'%s' cannot appear more than once in the same template" % bits[0]
    return ExtendsNode(nodelist, parent_name, parent_name_var)

def do_include(parser, token):
    """
    Loads a template and renders it with the current context.

    Example::

        {% include "foo/some_include" %}
    """

    bits = token.contents.split()
    if len(bits) != 2:
        raise TemplateSyntaxError, "%r tag takes one argument: the name of the template to be included" % bits[0]
    path = bits[1]
    if path[0] in ('"', "'") and path[-1] == path[0]:
        return ConstantIncludeNode(path[1:-1])
    return IncludeNode(bits[1])

register_tag('block', do_block)
register_tag('extends', do_extends)
register_tag('include', do_include)
