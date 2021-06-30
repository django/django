from mango.contrib.admin import (
    HORIZONTAL, VERTICAL, AdminSite, ModelAdmin, StackedInline, TabularInline,
    action, autodiscover, display, register, site,
)
from mango.contrib.gis.admin.options import GeoModelAdmin, OSMGeoAdmin
from mango.contrib.gis.admin.widgets import OpenLayersWidget

__all__ = [
    'HORIZONTAL', 'VERTICAL', 'AdminSite', 'ModelAdmin', 'StackedInline',
    'TabularInline', 'action', 'autodiscover', 'display', 'register', 'site',
    'GeoModelAdmin', 'OSMGeoAdmin', 'OpenLayersWidget',
]
