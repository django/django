import os, sys
from ctypes import CDLL

if os.name == 'nt':
    # Windows NT library
    lib_name = 'libgdal-1.dll'
elif os.name == 'posix':
    platform = os.uname()[0]
    if platform == 'Linux':
        # Linux shared library
        lib_name = 'libgdal.so'
    elif platform == 'Darwin':
        # Mac OSX Shared Library
        lib_name = 'libgdal.dylib'
    else:
        raise GDALException, 'Unknown POSIX platform "%s"' % platform
else:
    raise GDALException, 'Unsupported OS "%s"' % os.name

# The GDAL C library
lgdal = CDLL(lib_name)
                                                                            
