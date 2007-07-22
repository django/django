import os, sys
from ctypes import CDLL
from django.contrib.gis.gdal.error import OGRException

if os.name == 'nt':
    # Windows NT shared library
    lib_name = 'libgdal-1.dll'
elif os.name == 'posix':
    platform = os.uname()[0]
    if platform in ('Linux', 'SunOS'):
        # Linux or Solaris shared library
        lib_name = 'libgdal.so'
    elif platform == 'Darwin':
        # Mac OSX shared library
        lib_name = 'libgdal.dylib'
    else:
        raise OGRException, 'Unknown POSIX platform "%s"' % platform
else:
    raise OGRException, 'Unsupported OS "%s"' % os.name

# This loads the GDAL/OGR C library
lgdal = CDLL(lib_name)

