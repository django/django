"""
 This module contains useful utilities for GeoDjango.
"""

# Importing LayerMapping and ogrinfo (will not be done if GDAL is not
#  installed)
from django.contrib.gis.gdal import HAS_GDAL
if HAS_GDAL:
    from django.contrib.gis.utils.ogrinfo import ogrinfo, sample
    from django.contrib.gis.utils.layermapping import LayerMapping
    
# Importing GeoIP
try:
    from django.contrib.gis.utils.geoip import GeoIP
    HAS_GEOIP = True
except:
    HAS_GEOIP = False

