# Getting the normal admin routines, classes, and `site` instance.
from django.contrib.admin import (  # NOQA: flake8 detects only the last __all__
    autodiscover, site, AdminSite, ModelAdmin, StackedInline, TabularInline,
    HORIZONTAL, VERTICAL,
)
# Geographic admin options classes and widgets.
from django.contrib.gis.admin.options import GeoModelAdmin      # NOQA
from django.contrib.gis.admin.widgets import OpenLayersWidget   # NOQA

__all__ = [
    "autodiscover", "site", "AdminSite", "ModelAdmin", "StackedInline",
    "TabularInline", "HORIZONTAL", "VERTICAL",
    "GeoModelAdmin", "OpenLayersWidget", "HAS_OSM",
]

try:
    from django.contrib.gis.admin.options import OSMGeoAdmin
    HAS_OSM = True
    __all__ += ['OSMGeoAdmin']
except ImportError:
    HAS_OSM = False
