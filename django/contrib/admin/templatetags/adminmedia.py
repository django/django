from django.template import Library
register = Library()

def admin_media_prefix():
    try:
        from django.conf.settings import ADMIN_MEDIA_PREFIX
    except ImportError:
        return ''
    return ADMIN_MEDIA_PREFIX
admin_media_prefix = register.simple_tag(admin_media_prefix)