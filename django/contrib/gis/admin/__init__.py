from django.contrib.admin import (
    HORIZONTAL, VERTICAL, AdminSite, ModelAdmin, StackedInline, TabularInline,
    action, autodiscover, display, register, site,
)
from django.contrib.gis.admin.options import GeoModelAdmin, OSMGeoAdmin
from django.contrib.gis.admin.widgets import OpenLayersWidget

__all__ = [
    'HORIZONTAL', 'VERTICAL', 'AdminSite', 'ModelAdmin', 'StackedInline',
    'TabularInline', 'action', 'autodiscover', 'display', 'register', 'site',
    'GeoModelAdmin', 'OSMGeoAdmin', 'OpenLayersWidget',
]
