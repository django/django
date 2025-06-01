from ctypes import POINTER, c_char_p, c_int, c_void_p

from django.contrib.gis.gdal.prototypes.generation import (
    ConstStringOutput,
    DoubleOutput,
    IntOutput,
    SRSOutput,
    StringOutput,
    VoidOutput,
)


# Shortcut generation for routines with known parameters.
class SRSDouble(DoubleOutput):
    """
    Create a function prototype for the OSR routines that take
    the OSRSpatialReference object and return a double value.
    """

    argtypes = [c_void_p, POINTER(c_int)]
    errcheck = True


class UnitsFunc(DoubleOutput):
    """
    Create a function prototype for OSR units functions, e.g.,
    OSRGetAngularUnits, OSRGetLinearUnits.
    """

    argtypes = [c_void_p, POINTER(c_char_p)]

    def __init__(self, func_name, **kwargs):
        super().__init__(func_name, strarg=True, **kwargs)


# Creation & destruction.
clone_srs = SRSOutput("OSRClone", argtypes=[c_void_p])
new_srs = SRSOutput("OSRNewSpatialReference", argtypes=[c_char_p])
release_srs = VoidOutput("OSRRelease", argtypes=[c_void_p], errcheck=False)
destroy_srs = VoidOutput(
    "OSRDestroySpatialReference", argtypes=[c_void_p], errcheck=False
)
srs_validate = VoidOutput("OSRValidate", argtypes=[c_void_p])
set_axis_strategy = VoidOutput(
    "OSRSetAxisMappingStrategy", argtypes=[c_void_p, c_int], errcheck=False
)

# Getting the semi_major, semi_minor, and flattening functions.
semi_major = SRSDouble("OSRGetSemiMajor")
semi_minor = SRSDouble("OSRGetSemiMinor")
invflattening = SRSDouble("OSRGetInvFlattening")

# WKT, PROJ, EPSG, XML importation routines.
from_wkt = VoidOutput("OSRImportFromWkt", argtypes=[c_void_p, POINTER(c_char_p)])
from_proj = VoidOutput("OSRImportFromProj4", argtypes=[c_void_p, c_char_p])
from_epsg = VoidOutput("OSRImportFromEPSG", argtypes=[c_void_p, c_int])
from_xml = VoidOutput("OSRImportFromXML", argtypes=[c_void_p, c_char_p])
from_user_input = VoidOutput("OSRSetFromUserInput", argtypes=[c_void_p, c_char_p])

# Morphing to/from ESRI WKT.
morph_to_esri = VoidOutput("OSRMorphToESRI", argtypes=[c_void_p])
morph_from_esri = VoidOutput("OSRMorphFromESRI", argtypes=[c_void_p])

# Identifying the EPSG
identify_epsg = VoidOutput("OSRAutoIdentifyEPSG", argtypes=[c_void_p])

# Getting the angular_units, linear_units functions
linear_units = UnitsFunc("OSRGetLinearUnits")
angular_units = UnitsFunc("OSRGetAngularUnits")

# For exporting to WKT, PROJ, "Pretty" WKT, and XML.
to_wkt = StringOutput(
    "OSRExportToWkt", argtypes=[c_void_p, POINTER(c_char_p)], decoding="utf-8"
)
to_proj = StringOutput(
    "OSRExportToProj4", argtypes=[c_void_p, POINTER(c_char_p)], decoding="ascii"
)
to_pretty_wkt = StringOutput(
    "OSRExportToPrettyWkt",
    argtypes=[c_void_p, POINTER(c_char_p), c_int],
    offset=-2,
    decoding="utf-8",
)

to_xml = StringOutput(
    "OSRExportToXML",
    argtypes=[c_void_p, POINTER(c_char_p), c_char_p],
    offset=-2,
    decoding="utf-8",
)

# String attribute retrieval routines.
get_attr_value = ConstStringOutput(
    "OSRGetAttrValue", argtypes=[c_void_p, c_char_p, c_int], decoding="utf-8"
)
get_auth_name = ConstStringOutput(
    "OSRGetAuthorityName", argtypes=[c_void_p, c_char_p], decoding="ascii"
)
get_auth_code = ConstStringOutput(
    "OSRGetAuthorityCode", argtypes=[c_void_p, c_char_p], decoding="ascii"
)

# SRS Properties
isgeographic = IntOutput("OSRIsGeographic", argtypes=[c_void_p])
islocal = IntOutput("OSRIsLocal", argtypes=[c_void_p])
isprojected = IntOutput("OSRIsProjected", argtypes=[c_void_p])

# Coordinate transformation
new_ct = SRSOutput("OCTNewCoordinateTransformation", argtypes=[c_void_p, c_void_p])
destroy_ct = VoidOutput(
    "OCTDestroyCoordinateTransformation", argtypes=[c_void_p], errcheck=False
)
