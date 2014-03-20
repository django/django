"""
 This module houses the GeoIP object, a ctypes wrapper for the MaxMind GeoIP(R)
 C API (http://www.maxmind.com/app/c).  This is an alternative to the GPL
 licensed Python GeoIP interface provided by MaxMind.

 GeoIP(R) is a registered trademark of MaxMind, LLC of Boston, Massachusetts.

 For IP-based geolocation, this module requires the GeoLite Country and City
 datasets, in binary format (CSV will not work!).  The datasets may be
 downloaded from MaxMind at http://www.maxmind.com/download/geoip/database/.
 Grab GeoIP.dat.gz and GeoLiteCity.dat.gz, and unzip them in the directory
 corresponding to settings.GEOIP_PATH.
"""
__all__ = ['HAS_GEOIP']

try:
    from .base import GeoIP, GeoIPException
    HAS_GEOIP = True
    __all__ += ['GeoIP', 'GeoIPException']
except RuntimeError:  # libgeoip.py raises a RuntimeError if no GeoIP library is found
    HAS_GEOIP = False
