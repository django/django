# Getting the normal admin routines, classes, and `site` instance.
from django.contrib.admin import (  # NOQA: flake8 detects only the last __all__
    autodiscover, site, AdminSite, ModelAdmin, StackedInline, TabularInline,
    HORIZONTAL, VERTICAL,
)
# Geographic admin options classes and widgets.
from django.contrib.gis.admin.options import GeoModelAdmin, OSMGeoAdmin  # NOQA
from django.contrib.gis.admin.widgets import OpenLayersWidget   # NOQA
