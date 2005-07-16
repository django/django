from django.core import template

class AdminMediaPrefixNode(template.Node):
    def render(self, context):
        try:
            from django.conf.settings import ADMIN_MEDIA_PREFIX
        except ImportError:
            return ''
        return ADMIN_MEDIA_PREFIX

def admin_media_prefix(parser, token):
    """
    {% admin_media_prefix %}
    """
    bits = token.contents.split()
    return AdminMediaPrefixNode()

template.register_tag('admin_media_prefix', admin_media_prefix)
