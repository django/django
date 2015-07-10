import os
from ctypes import CDLL
from ctypes.util import find_library

from django.conf import settings

# Creating the settings dictionary with any settings, if needed.
GEOIP_SETTINGS = {key: getattr(settings, key)
                  for key in ('GEOIP_PATH', 'GEOIP_LIBRARY_PATH', 'GEOIP_COUNTRY', 'GEOIP_CITY')
                  if hasattr(settings, key)}
lib_path = GEOIP_SETTINGS.get('GEOIP_LIBRARY_PATH')

# The shared library for the GeoIP C API.  May be downloaded
#  from http://www.maxmind.com/download/geoip/api/c/
if lib_path:
    lib_name = None
else:
    # TODO: Is this really the library name for Windows?
    lib_name = 'GeoIP'

# Getting the path to the GeoIP library.
if lib_name:
    lib_path = find_library(lib_name)
if lib_path is None:
    raise RuntimeError('Could not find the GeoIP library (tried "%s"). '
                       'Try setting GEOIP_LIBRARY_PATH in your settings.' % lib_name)
lgeoip = CDLL(lib_path)

# Getting the C `free` for the platform.
if os.name == 'nt':
    libc = CDLL('msvcrt')
else:
    libc = CDLL(None)
free = libc.free
