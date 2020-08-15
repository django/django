"""
 This module contains useful utilities for GeoDjango.
"""
from django.contrib.gis.utils.ogrinfo import ogrinfo  # NOQA
from django.contrib.gis.utils.ogrinspect import mapping, ogrinspect  # NOQA
from django.contrib.gis.utils.srs import add_srs_entry  # NOQA
from django.core.exceptions import ImproperlyConfigured

try:
    # LayerMapping requires DJANGO_SETTINGS_MODULE to be set,
    # and ImproperlyConfigured is raised if that's not the case.
    from django.contrib.gis.utils.layermapping import (  # NOQA
        LayerMapError, LayerMapping,
    )
except ImproperlyConfigured:
    pass
