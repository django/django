from ctypes import POINTER, c_char_p, c_double, c_int, c_void_p

from django.contrib.gis.gdal.envelope import OGREnvelope
from django.contrib.gis.gdal.libgdal import GDAL_VERSION, lgdal
from django.contrib.gis.gdal.prototypes.errcheck import check_envelope
from django.contrib.gis.gdal.prototypes.generation import (
    bool_output,
    const_string_output,
    double_output,
    geom_output,
    int_output,
    srs_output,
    string_output,
    void_output,
)


# ### Generation routines specific to this module ###
def env_func(f, argtypes):
    "For getting OGREnvelopes."
    f.argtypes = argtypes
    f.restype = None
    f.errcheck = check_envelope
    return f


def pnt_func(f):
    "For accessing point information."
    return double_output(f, [c_void_p, c_int])


def topology_func(f):
    f.argtypes = [c_void_p, c_void_p]
    f.restype = c_int
    f.errcheck = lambda result, func, cargs: bool(result)
    return f


# ### OGR_G ctypes function prototypes ###

# GeoJSON routines.
from_json = geom_output(lgdal.OGR_G_CreateGeometryFromJson, [c_char_p])
to_json = string_output(
    lgdal.OGR_G_ExportToJson, [c_void_p], str_result=True, decoding="ascii"
)
to_kml = string_output(
    lgdal.OGR_G_ExportToKML, [c_void_p, c_char_p], str_result=True, decoding="ascii"
)

# GetX, GetY, GetZ all return doubles.
getx = pnt_func(lgdal.OGR_G_GetX)
gety = pnt_func(lgdal.OGR_G_GetY)
getz = pnt_func(lgdal.OGR_G_GetZ)
getm = pnt_func(lgdal.OGR_G_GetM)

# Geometry creation routines.
if GDAL_VERSION >= (3, 3):
    from_wkb = geom_output(
        lgdal.OGR_G_CreateFromWkbEx,
        [c_char_p, c_void_p, POINTER(c_void_p), c_int],
        offset=-2,
    )
else:
    from_wkb = geom_output(
        lgdal.OGR_G_CreateFromWkb,
        [c_char_p, c_void_p, POINTER(c_void_p), c_int],
        offset=-2,
    )
from_wkt = geom_output(
    lgdal.OGR_G_CreateFromWkt,
    [POINTER(c_char_p), c_void_p, POINTER(c_void_p)],
    offset=-1,
)
from_gml = geom_output(lgdal.OGR_G_CreateFromGML, [c_char_p])
create_geom = geom_output(lgdal.OGR_G_CreateGeometry, [c_int])
clone_geom = geom_output(lgdal.OGR_G_Clone, [c_void_p])
get_geom_ref = geom_output(lgdal.OGR_G_GetGeometryRef, [c_void_p, c_int])
get_boundary = geom_output(lgdal.OGR_G_GetBoundary, [c_void_p])
geom_convex_hull = geom_output(lgdal.OGR_G_ConvexHull, [c_void_p])
geom_diff = geom_output(lgdal.OGR_G_Difference, [c_void_p, c_void_p])
geom_intersection = geom_output(lgdal.OGR_G_Intersection, [c_void_p, c_void_p])
geom_sym_diff = geom_output(lgdal.OGR_G_SymmetricDifference, [c_void_p, c_void_p])
geom_union = geom_output(lgdal.OGR_G_Union, [c_void_p, c_void_p])
is_3d = bool_output(lgdal.OGR_G_Is3D, [c_void_p])
set_3d = void_output(lgdal.OGR_G_Set3D, [c_void_p, c_int], errcheck=False)
is_measured = bool_output(lgdal.OGR_G_IsMeasured, [c_void_p])
set_measured = void_output(lgdal.OGR_G_SetMeasured, [c_void_p, c_int], errcheck=False)
has_curve_geom = bool_output(lgdal.OGR_G_HasCurveGeometry, [c_void_p, c_int])
get_linear_geom = geom_output(
    lgdal.OGR_G_GetLinearGeometry, [c_void_p, c_double, POINTER(c_char_p)]
)
get_curve_geom = geom_output(
    lgdal.OGR_G_GetCurveGeometry, [c_void_p, POINTER(c_char_p)]
)

# Geometry modification routines.
add_geom = void_output(lgdal.OGR_G_AddGeometry, [c_void_p, c_void_p])
import_wkt = void_output(lgdal.OGR_G_ImportFromWkt, [c_void_p, POINTER(c_char_p)])

# Destroys a geometry
destroy_geom = void_output(lgdal.OGR_G_DestroyGeometry, [c_void_p], errcheck=False)

# Geometry export routines.
to_wkb = void_output(
    lgdal.OGR_G_ExportToWkb, None, errcheck=True
)  # special handling for WKB.
to_iso_wkb = void_output(lgdal.OGR_G_ExportToIsoWkb, None, errcheck=True)
to_wkt = string_output(
    lgdal.OGR_G_ExportToWkt, [c_void_p, POINTER(c_char_p)], decoding="ascii"
)
to_iso_wkt = string_output(
    lgdal.OGR_G_ExportToIsoWkt, [c_void_p, POINTER(c_char_p)], decoding="ascii"
)
to_gml = string_output(
    lgdal.OGR_G_ExportToGML, [c_void_p], str_result=True, decoding="ascii"
)
if GDAL_VERSION >= (3, 3):
    get_wkbsize = int_output(lgdal.OGR_G_WkbSizeEx, [c_void_p])
else:
    get_wkbsize = int_output(lgdal.OGR_G_WkbSize, [c_void_p])

# Geometry spatial-reference related routines.
assign_srs = void_output(
    lgdal.OGR_G_AssignSpatialReference, [c_void_p, c_void_p], errcheck=False
)
get_geom_srs = srs_output(lgdal.OGR_G_GetSpatialReference, [c_void_p])

# Geometry properties
get_area = double_output(lgdal.OGR_G_GetArea, [c_void_p])
get_centroid = void_output(lgdal.OGR_G_Centroid, [c_void_p, c_void_p])
get_dims = int_output(lgdal.OGR_G_GetDimension, [c_void_p])
get_coord_dim = int_output(lgdal.OGR_G_CoordinateDimension, [c_void_p])
set_coord_dim = void_output(
    lgdal.OGR_G_SetCoordinateDimension, [c_void_p, c_int], errcheck=False
)
is_empty = int_output(
    lgdal.OGR_G_IsEmpty, [c_void_p], errcheck=lambda result, func, cargs: bool(result)
)

get_geom_count = int_output(lgdal.OGR_G_GetGeometryCount, [c_void_p])
get_geom_name = const_string_output(
    lgdal.OGR_G_GetGeometryName, [c_void_p], decoding="ascii"
)
get_geom_type = int_output(lgdal.OGR_G_GetGeometryType, [c_void_p])
get_point_count = int_output(lgdal.OGR_G_GetPointCount, [c_void_p])
get_point = void_output(
    lgdal.OGR_G_GetPointZM,
    [
        c_void_p,
        c_int,
        POINTER(c_double),
        POINTER(c_double),
        POINTER(c_double),
        POINTER(c_double),
    ],
    errcheck=False,
)
geom_close_rings = void_output(lgdal.OGR_G_CloseRings, [c_void_p], errcheck=False)

# Topology routines.
ogr_contains = topology_func(lgdal.OGR_G_Contains)
ogr_crosses = topology_func(lgdal.OGR_G_Crosses)
ogr_disjoint = topology_func(lgdal.OGR_G_Disjoint)
ogr_equals = topology_func(lgdal.OGR_G_Equals)
ogr_intersects = topology_func(lgdal.OGR_G_Intersects)
ogr_overlaps = topology_func(lgdal.OGR_G_Overlaps)
ogr_touches = topology_func(lgdal.OGR_G_Touches)
ogr_within = topology_func(lgdal.OGR_G_Within)

# Transformation routines.
geom_transform = void_output(lgdal.OGR_G_Transform, [c_void_p, c_void_p])
geom_transform_to = void_output(lgdal.OGR_G_TransformTo, [c_void_p, c_void_p])

# For retrieving the envelope of the geometry.
get_envelope = env_func(lgdal.OGR_G_GetEnvelope, [c_void_p, POINTER(OGREnvelope)])
