from django.contrib.admin import (
    HORIZONTAL, VERTICAL, AdminSite, ModelAdmin, StackedInline, TabularInline,
    autodiscover, site,
)
from django.contrib.gis.admin.options import GeoModelAdmin, OSMGeoAdmin
from django.contrib.gis.admin.widgets import OpenLayersWidget

__all__ = [
    'autodiscover', 'site', 'AdminSite', 'ModelAdmin', 'StackedInline',
    'TabularInline', 'HORIZONTAL', 'VERTICAL', 'GeoModelAdmin', 'OSMGeoAdmin',
    'OpenLayersWidget',
]
