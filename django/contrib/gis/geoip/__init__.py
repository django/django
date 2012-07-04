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
from __future__ import absolute_import

try:
    from .base import GeoIP, GeoIPException
    HAS_GEOIP = True
except:
    HAS_GEOIP = False
