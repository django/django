"""
 This module contains useful utilities for GeoDjango.
"""
from django.contrib.gis.utils.ogrinfo import ogrinfo
from django.contrib.gis.utils.ogrinspect import mapping, ogrinspect
from django.contrib.gis.utils.srs import add_srs_entry
from django.core.exceptions import ImproperlyConfigured

__all__ = [
    "add_srs_entry",
    "mapping",
    "ogrinfo",
    "ogrinspect",
]

try:
    # LayerMapping requires DJANGO_SETTINGS_MODULE to be set,
    # and ImproperlyConfigured is raised if that's not the case.
    from django.contrib.gis.utils.layermapping import LayerMapError, LayerMapping

    __all__ += ["LayerMapError", "LayerMapping"]

except ImproperlyConfigured:
    pass
