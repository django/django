from django import template
from django.template import loader
from django.conf import settings

register = template.Library()

def if_has_perm(parser, token):
    """
    TODO: Update document

    Checks permission on the given user. Checks row-level permissions if an
    object is given.

    Perm name should be in the format [app_label].[perm codename].
    """
    tokens = token.split_contents()
    if len(tokens) < 2:
        raise template.TemplateSyntaxError, "%r tag requires at least 1 argument" % tokens[0]
    if len(tokens) > 4:
        raise template.TemplateSyntaxError, "%r tag should have no more then 3 arguments" % tokens[0]

    nodelist_true = parser.parse(('else', 'end_'+tokens[0],))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('end_'+tokens[0],))
        parser.delete_first_token()
    else:
        nodelist_false = template.NodeList()

    object_var = None
    not_flag = False
    if tokens[1] == "not":
        not_flag = True
        permission = tokens[2]
        if len(tokens) > 3:
            object_var = parser.compile_filter(tokens[3])
    else:
        permission = tokens[1]
        if len(tokens) > 2:
            object_var = parser.compile_filter(tokens[2])

    if not (permission[0] == permission[-1] and permission[0] in ('"', "'")):
        raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tokens[0]

    return HasPermNode(permission[1:-1], not_flag, object_var, nodelist_true, nodelist_false)

class HasPermNode(template.Node):
    def __init__(self, permission, not_flag, object_var, nodelist_true, nodelist_false):
        self.permission = permission
        self.not_flag = not_flag
        self.object_var = object_var
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false

    def __repr__(self):
        return "<HasPerm node>"

    def __iter__(self):
        for node in self.nodelist_true:
            yield node
        for node in self.nodelist_false:
            yield node

    def get_nodes_by_type(self, nodetype):
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        nodes.extend(self.nodelist_true.get_nodes_by_type(nodetype))
        nodes.extend(self.nodelist_false.get_nodes_by_type(nodetype))
        return nodes

    def render(self, context):
        if self.object_var:
            try:
                object = self.object_var.resolve(context)
            except template.VariableDoesNotExist:
                object = None
        else:
            object=None

        try:
            user = template.resolve_variable("user", context)
        except template.VariableDoesNotExist:
            return settings.TEMPLATE_STRING_IF_INVALID

        bool_perm = user.has_perm(self.permission, object=object)
        if (self.not_flag and not bool_perm) or (not self.not_flag and bool_perm):
            return self.nodelist_true.render(context)
        if (self.not_flag and bool_perm) or (not self.not_flag and not bool_perm):
            return self.nodelist_false.render(context)
        return ''

register.tag('if_has_perm', if_has_perm)
