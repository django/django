import sha
from django.contrib.contenttypes.models import ContentType
from django import template
from django.conf import settings 

register = template.Library()

#Based off work by Ian Holsman
#http://svn.zyons.python-hosting.com/trunk/zilbo/common/utils/templatetags/media.py
class objref_class(template.Node):
    """ return a object reference to a given object """
    def __init__(self, obj):
        self.object_name= obj 

    def render(self, context):
        object_id = template.resolve_variable( self.object_name, context ) 
        c_obj = ContentType.objects.get_for_model( object_id ).id
        #c_obj = get_content_type_id( object_id )
        return "%s/%d/%s" % ( c_obj, object_id.id, sha.new("%s/%d" % (c_obj, object_id.id) + settings.SECRET_KEY).hexdigest())

#Based off work by Ian Holsman
#http://svn.zyons.python-hosting.com/trunk/zilbo/common/utils/templatetags/media.py
def objref(parser, token):
    """
    {% objref <object> %} 
    """
    bits = token.contents.split()
    tok=""
    if len(bits) > 2:
        raise template.TemplateSyntaxError, "'objref' statements must be 'objref <object>': %s" % token.contents
    if len(bits) == 2:
        tok = bits[1]
    else:
        tok = "object"
    return objref_class(tok)

def check_rlp_inline(parser, token):
    tokens = token.split_contents()
    if len(tokens)!=2:
        raise template.TemplateSyntaxError, "%r tag requires only 1 arguments" % tokens[0]
    
    nodelist = parser.parse(('end_'+tokens[0],))
    token = parser.next_token()    
    
    object_var = parser.compile_filter(tokens[1])
    
    return CheckRLPInlineNode(object_var, nodelist)

class CheckRLPInlineNode(template.Node):
    def __init__(self, object_var, nodelist):
        self.object_var = object_var
        self.nodelist = nodelist
        
    def render(self, context):
        if self.object_var:
            try:
                object = self.object_var.resolve(context)
            except template.VariableDoesNotExist:
                return self.nodelist.render(context)
        else:
            return self.nodelist.render(context)
        
        if object is None:
            return self.nodelist.render(context)            
        
        if not object._meta.row_level_permissions:
            return self.nodelist.render(context)
        
        try:
            user = template.resolve_variable("user", context)
        except template.VariableDoesNotExist:
            return settings.TEMPLATE_STRING_IF_INVALID
        
        permission = object._meta.get_change_permission()
        
        bool_perm = user.has_perm(object._meta.app_label+'.'+permission, object=object)
        
        if bool_perm:
            return self.nodelist.render(context)
        return ""
        
        
        
        

#From: http://code.djangoproject.com/wiki/PaginatorTag
def paginator(context, adjacent_pages=2):
    """Adds pagination context variables for first, adjacent and next page links
    in addition to those already populated by the object_list generic view."""
    page_numbers = [n for n in \
                    range(context["page"] - adjacent_pages, context["page"] + adjacent_pages + 1) \
                    if n > 0 and n <= context["pages"]]
    return {
        "hits": context["hits"],
        "results_per_page": context["results_per_page"],
        "page": context["page"],
        "pages": context["pages"],
        "page_numbers": page_numbers,
        "next": context["next"],
        "previous": context["previous"],
        "has_next": context["has_next"],
        "has_previous": context["has_previous"],
        "show_first": 1 not in page_numbers,
        "show_last": context["pages"] not in page_numbers,
    }

register.inclusion_tag("admin/paginator.html", takes_context=True)(paginator)

register.tag('objref', objref)
register.tag('check_rlp_inline', check_rlp_inline)