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

register.tag('objref', objref)