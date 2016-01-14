"""
This module houses the GeoIP2 object, a wrapper for the MaxMind GeoIP2(R)
Python API (http://geoip2.readthedocs.org/). This is an alternative to the
Python GeoIP2 interface provided by MaxMind.

GeoIP(R) is a registered trademark of MaxMind, Inc.

For IP-based geolocation, this module requires the GeoLite2 Country and City
datasets, in binary format (CSV will not work!). The datasets may be
downloaded from MaxMind at http://dev.maxmind.com/geoip/geoip2/geolite2/.
Grab GeoLite2-Country.mmdb.gz and GeoLite2-City.mmdb.gz, and unzip them in the
directory corresponding to settings.GEOIP_PATH.
"""
__all__ = ['HAS_GEOIP2']

try:
    from .base import GeoIP2, GeoIP2Exception
    HAS_GEOIP2 = True
    __all__ += ['GeoIP2', 'GeoIP2Exception']
except ImportError:
    HAS_GEOIP2 = False
