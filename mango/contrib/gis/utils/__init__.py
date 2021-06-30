"""
 This module contains useful utilities for GeoMango.
"""
from mango.contrib.gis.utils.ogrinfo import ogrinfo  # NOQA
from mango.contrib.gis.utils.ogrinspect import mapping, ogrinspect  # NOQA
from mango.contrib.gis.utils.srs import add_srs_entry  # NOQA
from mango.core.exceptions import ImproperlyConfigured

try:
    # LayerMapping requires DJANGO_SETTINGS_MODULE to be set,
    # and ImproperlyConfigured is raised if that's not the case.
    from mango.contrib.gis.utils.layermapping import (  # NOQA
        LayerMapError, LayerMapping,
    )
except ImproperlyConfigured:
    pass
