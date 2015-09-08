"""
PostGIS to GDAL conversion constant definitions
"""
# Lookup to convert pixel type values from GDAL to PostGIS
GDAL_TO_POSTGIS = [None, 4, 6, 5, 8, 7, 10, 11, None, None, None, None]

# Lookup to convert pixel type values from PostGIS to GDAL
POSTGIS_TO_GDAL = [1, 1, 1, 3, 1, 3, 2, 5, 4, None, 6, 7, None, None]

# Struct pack structure for raster header, the raster header has the
# following structure:
#
# Endianness, PostGIS raster version, number of bands, scale, origin,
# skew, srid, width, and height.
#
# Scale, origin, and skew have x and y values. PostGIS currently uses
# a fixed endianness (1) and there is only one version (0).
POSTGIS_HEADER_STRUCTURE = 'B H H d d d d d d i H H'

# Lookup values to convert GDAL pixel types to struct characters. This is
# used to pack and unpack the pixel values of PostGIS raster bands.
GDAL_TO_STRUCT = [
    None, 'B', 'H', 'h', 'L', 'l', 'f', 'd',
    None, None, None, None,
]

# Size of the packed value in bytes for different numerical types.
# This is needed to cut chunks of band data out of PostGIS raster strings
# when decomposing them into GDALRasters.
# See https://docs.python.org/3/library/struct.html#format-characters
STRUCT_SIZE = {
    'b': 1,  # Signed char
    'B': 1,  # Unsigned char
    '?': 1,  # _Bool
    'h': 2,  # Short
    'H': 2,  # Unsigned short
    'i': 4,  # Integer
    'I': 4,  # Unsigned Integer
    'l': 4,  # Long
    'L': 4,  # Unsigned Long
    'f': 4,  # Float
    'd': 8,  # Double
}
