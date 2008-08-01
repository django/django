from django.contrib.admin.options import ModelAdmin, HORIZONTAL, VERTICAL
from django.contrib.admin.options import StackedInline, TabularInline
from django.contrib.admin.sites import AdminSite, site

def autodiscover():
    """
    Auto-discover INSTALLED_APPS admin.py modules and fail silently when 
    not present. This forces an import on them to register any admin bits they
    may want.
    """
    from django.conf import settings
    for app in settings.INSTALLED_APPS:
        try:
            __import__("%s.admin" % app)
        except ImportError:
            pass
