"""
 This module contains useful utilities for GeoDjango.
"""
# Importing the utilities that depend on GDAL, if available.
from django.contrib.gis.gdal import HAS_GDAL
if HAS_GDAL:
    from django.contrib.gis.utils.ogrinfo import ogrinfo, sample
    from django.contrib.gis.utils.ogrinspect import mapping, ogrinspect
    from django.contrib.gis.utils.srs import add_postgis_srs, add_srs_entry
    try:
        # LayerMapping requires DJANGO_SETTINGS_MODULE to be set,
        # so this needs to be in try/except.
        from django.contrib.gis.utils.layermapping import LayerMapping, LayerMapError
    except:
        pass

from django.contrib.gis.utils.wkt import precision_wkt
