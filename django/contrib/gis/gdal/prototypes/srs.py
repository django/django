from ctypes import c_char_p, c_int, c_void_p, POINTER
from django.contrib.gis.gdal.libgdal import lgdal, std_call
from django.contrib.gis.gdal.prototypes.generation import \
    const_string_output, double_output, int_output, \
    srs_output, string_output, void_output

## Shortcut generation for routines with known parameters.
def srs_double(f):
    """
    Creates a function prototype for the OSR routines that take
    the OSRSpatialReference object and
    """
    return double_output(f, [c_void_p, POINTER(c_int)], errcheck=True)

def units_func(f):
    """
    Creates a ctypes function prototype for OSR units functions, e.g.,
    OSRGetAngularUnits, OSRGetLinearUnits.
    """
    return double_output(f, [c_void_p, POINTER(c_char_p)], strarg=True)

# Creation & destruction.
clone_srs = srs_output(std_call('OSRClone'), [c_void_p])
new_srs = srs_output(std_call('OSRNewSpatialReference'), [c_char_p])
release_srs = void_output(lgdal.OSRRelease, [c_void_p], errcheck=False)
destroy_srs = void_output(std_call('OSRDestroySpatialReference'), [c_void_p], errcheck=False)
srs_validate = void_output(lgdal.OSRValidate, [c_void_p])

# Getting the semi_major, semi_minor, and flattening functions.
semi_major = srs_double(lgdal.OSRGetSemiMajor)
semi_minor = srs_double(lgdal.OSRGetSemiMinor)
invflattening = srs_double(lgdal.OSRGetInvFlattening)

# WKT, PROJ, EPSG, XML importation routines.
from_wkt = void_output(lgdal.OSRImportFromWkt, [c_void_p, POINTER(c_char_p)])
from_proj = void_output(lgdal.OSRImportFromProj4, [c_void_p, c_char_p])
from_epsg = void_output(std_call('OSRImportFromEPSG'), [c_void_p, c_int])
from_xml = void_output(lgdal.OSRImportFromXML, [c_void_p, c_char_p])

# Morphing to/from ESRI WKT.
morph_to_esri = void_output(lgdal.OSRMorphToESRI, [c_void_p])
morph_from_esri = void_output(lgdal.OSRMorphFromESRI, [c_void_p])

# Identifying the EPSG
identify_epsg = void_output(lgdal.OSRAutoIdentifyEPSG, [c_void_p])

# Getting the angular_units, linear_units functions
linear_units = units_func(lgdal.OSRGetLinearUnits)
angular_units = units_func(lgdal.OSRGetAngularUnits)

# For exporting to WKT, PROJ.4, "Pretty" WKT, and XML.
to_wkt = string_output(std_call('OSRExportToWkt'), [c_void_p, POINTER(c_char_p)])
to_proj = string_output(std_call('OSRExportToProj4'), [c_void_p, POINTER(c_char_p)])
to_pretty_wkt = string_output(std_call('OSRExportToPrettyWkt'), [c_void_p, POINTER(c_char_p), c_int], offset=-2)

# Memory leak fixed in GDAL 1.5; still exists in 1.4.
to_xml = string_output(lgdal.OSRExportToXML, [c_void_p, POINTER(c_char_p), c_char_p], offset=-2)

# String attribute retrival routines.
get_attr_value = const_string_output(std_call('OSRGetAttrValue'), [c_void_p, c_char_p, c_int])
get_auth_name = const_string_output(lgdal.OSRGetAuthorityName, [c_void_p, c_char_p])
get_auth_code = const_string_output(lgdal.OSRGetAuthorityCode, [c_void_p, c_char_p])

# SRS Properties
isgeographic = int_output(lgdal.OSRIsGeographic, [c_void_p])
islocal = int_output(lgdal.OSRIsLocal, [c_void_p])
isprojected = int_output(lgdal.OSRIsProjected, [c_void_p])

# Coordinate transformation
new_ct= srs_output(std_call('OCTNewCoordinateTransformation'), [c_void_p, c_void_p])
destroy_ct = void_output(std_call('OCTDestroyCoordinateTransformation'), [c_void_p], errcheck=False)
