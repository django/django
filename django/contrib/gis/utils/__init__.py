from django.contrib.gis.utils.layermapping import LayerMapping
from django.contrib.gis.utils.inspect_data import sample

# Importing GeoIP
try:
    from django.contrib.gis.utils.geoip import GeoIP
    HAS_GEOIP = True
except:
    HAS_GEOIP = False
