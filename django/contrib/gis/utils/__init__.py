"""
This module contains useful utilities for GeoDjango.
"""

from django.contrib.gis.utils.layermapping import LayerMapError, LayerMapping
from django.contrib.gis.utils.ogrinfo import ogrinfo
from django.contrib.gis.utils.ogrinspect import mapping, ogrinspect
from django.contrib.gis.utils.srs import add_srs_entry

__all__ = [
    "add_srs_entry",
    "mapping",
    "ogrinfo",
    "ogrinspect",
    "LayerMapError",
    "LayerMapping",
]
