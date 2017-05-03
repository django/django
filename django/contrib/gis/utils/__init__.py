"""
 This module contains useful utilities for GeoDjango.
"""
from django.contrib.gis.utils.ogrinfo import ogrinfo  # NOQA
from django.contrib.gis.utils.ogrinspect import mapping, ogrinspect  # NOQA
from django.contrib.gis.utils.srs import add_srs_entry  # NOQA
from django.contrib.gis.utils.wkt import precision_wkt  # NOQA
from django.core.exceptions import ImproperlyConfigured

try:
    # LayerMapping requires DJANGO_SETTINGS_MODULE to be set,
    # so this needs to be in try/except.
    from django.contrib.gis.utils.layermapping import LayerMapping, LayerMapError  # NOQA
except ImproperlyConfigured:
    pass
