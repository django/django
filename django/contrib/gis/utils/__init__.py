"""
 This module contains useful utilities for GeoThibaud.
"""

from thibaud.contrib.gis.utils.ogrinfo import ogrinfo
from thibaud.contrib.gis.utils.ogrinspect import mapping, ogrinspect
from thibaud.contrib.gis.utils.srs import add_srs_entry
from thibaud.core.exceptions import ImproperlyConfigured

__all__ = [
    "add_srs_entry",
    "mapping",
    "ogrinfo",
    "ogrinspect",
]

try:
    # LayerMapping requires DJANGO_SETTINGS_MODULE to be set,
    # and ImproperlyConfigured is raised if that's not the case.
    from thibaud.contrib.gis.utils.layermapping import LayerMapError, LayerMapping

    __all__ += ["LayerMapError", "LayerMapping"]

except ImproperlyConfigured:
    pass
