"""
GDAL - Constant definitions
"""
from ctypes import (
    c_double, c_float, c_int16, c_int32, c_ubyte, c_uint16, c_uint32,
)

# See https://gdal.org/api/raster_c_api.html#_CPPv412GDALDataType
GDAL_PIXEL_TYPES = {
    0: 'GDT_Unknown',  # Unknown or unspecified type
    1: 'GDT_Byte',  # Eight bit unsigned integer
    2: 'GDT_UInt16',  # Sixteen bit unsigned integer
    3: 'GDT_Int16',  # Sixteen bit signed integer
    4: 'GDT_UInt32',  # Thirty-two bit unsigned integer
    5: 'GDT_Int32',  # Thirty-two bit signed integer
    6: 'GDT_Float32',  # Thirty-two bit floating point
    7: 'GDT_Float64',  # Sixty-four bit floating point
    8: 'GDT_CInt16',  # Complex Int16
    9: 'GDT_CInt32',  # Complex Int32
    10: 'GDT_CFloat32',  # Complex Float32
    11: 'GDT_CFloat64',  # Complex Float64
}

# A list of gdal datatypes that are integers.
GDAL_INTEGER_TYPES = [1, 2, 3, 4, 5]

# Lookup values to convert GDAL pixel type indices into ctypes objects.
# The GDAL band-io works with ctypes arrays to hold data to be written
# or to hold the space for data to be read into. The lookup below helps
# selecting the right ctypes object for a given gdal pixel type.
GDAL_TO_CTYPES = [
    None, c_ubyte, c_uint16, c_int16, c_uint32, c_int32,
    c_float, c_double, None, None, None, None
]

# List of resampling algorithms that can be used to warp a GDALRaster.
GDAL_RESAMPLE_ALGORITHMS = {
    'NearestNeighbour': 0,
    'Bilinear': 1,
    'Cubic': 2,
    'CubicSpline': 3,
    'Lanczos': 4,
    'Average': 5,
    'Mode': 6,
}

# See https://gdal.org/api/raster_c_api.html#_CPPv415GDALColorInterp
GDAL_COLOR_TYPES = {
    0: 'GCI_Undefined',  # Undefined, default value, i.e. not known
    1: 'GCI_GrayIndex',  # Greyscale
    2: 'GCI_PaletteIndex',  # Paletted
    3: 'GCI_RedBand',  # Red band of RGBA image
    4: 'GCI_GreenBand',  # Green band of RGBA image
    5: 'GCI_BlueBand',  # Blue band of RGBA image
    6: 'GCI_AlphaBand',  # Alpha (0=transparent, 255=opaque)
    7: 'GCI_HueBand',  # Hue band of HLS image
    8: 'GCI_SaturationBand',  # Saturation band of HLS image
    9: 'GCI_LightnessBand',  # Lightness band of HLS image
    10: 'GCI_CyanBand',  # Cyan band of CMYK image
    11: 'GCI_MagentaBand',  # Magenta band of CMYK image
    12: 'GCI_YellowBand',  # Yellow band of CMYK image
    13: 'GCI_BlackBand',  # Black band of CMLY image
    14: 'GCI_YCbCr_YBand',  # Y Luminance
    15: 'GCI_YCbCr_CbBand',  # Cb Chroma
    16: 'GCI_YCbCr_CrBand',  # Cr Chroma, also GCI_Max
}

# Fixed base path for buffer-based GDAL in-memory files.
VSI_FILESYSTEM_BASE_PATH = '/vsimem/'

# Should the memory file system take ownership of the buffer, freeing it when
# the file is deleted? (No, GDALRaster.__del__() will delete the buffer.)
VSI_TAKE_BUFFER_OWNERSHIP = False

# Should a VSI file be removed when retrieving its buffer?
VSI_DELETE_BUFFER_ON_READ = False
