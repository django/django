from ctypes import POINTER, c_char_p, c_double, c_int, c_void_p

from django.contrib.gis.gdal.envelope import OGREnvelope
from django.contrib.gis.gdal.libgdal import GDALFuncFactory
from django.contrib.gis.gdal.prototypes.errcheck import check_envelope
from django.contrib.gis.gdal.prototypes.generation import (
    BoolOutput,
    ConstStringOutput,
    DoubleOutput,
    GeomOutput,
    IntOutput,
    SRSOutput,
    StringOutput,
    VoidOutput,
)
from django.utils.functional import cached_property


class LazyGeomFunction:
    """A wrapper that lazily creates geometry functions based on GDAL version."""

    def __init__(self, func):
        self._func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    @cached_property
    def func(self):
        return self._func()


# ### Generation routines specific to this module ###
class EnvFunc(GDALFuncFactory):
    """For getting OGREnvelopes."""

    restype = None
    errcheck = staticmethod(check_envelope)


class PntFunc(GDALFuncFactory):
    """For accessing point information."""

    argtypes = [c_void_p, c_int]
    restype = c_double


class TopologyFunc(GDALFuncFactory):
    """For topology functions."""

    argtypes = [c_void_p, c_void_p]
    restype = c_int
    errcheck = staticmethod(lambda result, func, cargs: bool(result))


# ### OGR_G ctypes function prototypes ###

# GeoJSON routines.
from_json = GeomOutput("OGR_G_CreateGeometryFromJson", argtypes=[c_char_p])
to_json = StringOutput(
    "OGR_G_ExportToJson", argtypes=[c_void_p], str_result=True, decoding="ascii"
)
to_kml = StringOutput(
    "OGR_G_ExportToKML",
    argtypes=[c_void_p, c_char_p],
    str_result=True,
    decoding="ascii",
)

# GetX, GetY, GetZ all return doubles.
getx = PntFunc("OGR_G_GetX")
gety = PntFunc("OGR_G_GetY")
getz = PntFunc("OGR_G_GetZ")
getm = PntFunc("OGR_G_GetM")


# Geometry creation routines.
def _from_wkb():
    from django.contrib.gis.gdal.libgdal import GDAL_VERSION

    if GDAL_VERSION >= (3, 3):
        return GeomOutput(
            "OGR_G_CreateFromWkbEx",
            argtypes=[c_char_p, c_void_p, POINTER(c_void_p), c_int],
            offset=-2,
        )
    else:
        return GeomOutput(
            "OGR_G_CreateFromWkb",
            argtypes=[c_char_p, c_void_p, POINTER(c_void_p), c_int],
            offset=-2,
        )


from_wkb = LazyGeomFunction(_from_wkb)
from_wkt = GeomOutput(
    "OGR_G_CreateFromWkt",
    argtypes=[POINTER(c_char_p), c_void_p, POINTER(c_void_p)],
    offset=-1,
)
from_gml = GeomOutput("OGR_G_CreateFromGML", argtypes=[c_char_p])
create_geom = GeomOutput("OGR_G_CreateGeometry", argtypes=[c_int])
clone_geom = GeomOutput("OGR_G_Clone", argtypes=[c_void_p])
get_geom_ref = GeomOutput("OGR_G_GetGeometryRef", argtypes=[c_void_p, c_int])
get_boundary = GeomOutput("OGR_G_GetBoundary", argtypes=[c_void_p])
geom_convex_hull = GeomOutput("OGR_G_ConvexHull", argtypes=[c_void_p])
geom_diff = GeomOutput("OGR_G_Difference", argtypes=[c_void_p, c_void_p])
geom_intersection = GeomOutput("OGR_G_Intersection", argtypes=[c_void_p, c_void_p])
geom_sym_diff = GeomOutput("OGR_G_SymmetricDifference", argtypes=[c_void_p, c_void_p])
geom_union = GeomOutput("OGR_G_Union", argtypes=[c_void_p, c_void_p])
is_3d = BoolOutput("OGR_G_Is3D", argtypes=[c_void_p])
set_3d = VoidOutput("OGR_G_Set3D", argtypes=[c_void_p, c_int], errcheck=False)
is_measured = BoolOutput("OGR_G_IsMeasured", argtypes=[c_void_p])
set_measured = VoidOutput(
    "OGR_G_SetMeasured", argtypes=[c_void_p, c_int], errcheck=False
)
has_curve_geom = BoolOutput("OGR_G_HasCurveGeometry", argtypes=[c_void_p, c_int])
get_linear_geom = GeomOutput(
    "OGR_G_GetLinearGeometry", argtypes=[c_void_p, c_double, POINTER(c_char_p)]
)
get_curve_geom = GeomOutput(
    "OGR_G_GetCurveGeometry", argtypes=[c_void_p, POINTER(c_char_p)]
)

# Geometry modification routines.
add_geom = VoidOutput("OGR_G_AddGeometry", argtypes=[c_void_p, c_void_p])
import_wkt = VoidOutput("OGR_G_ImportFromWkt", argtypes=[c_void_p, POINTER(c_char_p)])

# Destroys a geometry
destroy_geom = VoidOutput("OGR_G_DestroyGeometry", argtypes=[c_void_p], errcheck=False)

# Geometry export routines.
to_wkb = VoidOutput(
    "OGR_G_ExportToWkb", argtypes=None, errcheck=True
)  # special handling for WKB.
to_iso_wkb = VoidOutput("OGR_G_ExportToIsoWkb", argtypes=None, errcheck=True)
to_wkt = StringOutput(
    "OGR_G_ExportToWkt", argtypes=[c_void_p, POINTER(c_char_p)], decoding="ascii"
)
to_iso_wkt = StringOutput(
    "OGR_G_ExportToIsoWkt", argtypes=[c_void_p, POINTER(c_char_p)], decoding="ascii"
)
to_gml = StringOutput(
    "OGR_G_ExportToGML", argtypes=[c_void_p], str_result=True, decoding="ascii"
)


def _get_wkbsize():
    from django.contrib.gis.gdal.libgdal import GDAL_VERSION

    if GDAL_VERSION >= (3, 3):
        return IntOutput("OGR_G_WkbSizeEx", argtypes=[c_void_p])
    else:
        return IntOutput("OGR_G_WkbSize", argtypes=[c_void_p])


get_wkbsize = LazyGeomFunction(_get_wkbsize)

# Geometry spatial-reference related routines.
assign_srs = VoidOutput(
    "OGR_G_AssignSpatialReference", argtypes=[c_void_p, c_void_p], errcheck=False
)
get_geom_srs = SRSOutput("OGR_G_GetSpatialReference", argtypes=[c_void_p])

# Geometry properties
get_area = DoubleOutput("OGR_G_GetArea", argtypes=[c_void_p])
get_centroid = VoidOutput("OGR_G_Centroid", argtypes=[c_void_p, c_void_p])
get_dims = IntOutput("OGR_G_GetDimension", argtypes=[c_void_p])
get_coord_dim = IntOutput("OGR_G_CoordinateDimension", argtypes=[c_void_p])
set_coord_dim = VoidOutput(
    "OGR_G_SetCoordinateDimension", argtypes=[c_void_p, c_int], errcheck=False
)
is_empty = BoolOutput("OGR_G_IsEmpty", argtypes=[c_void_p])

get_geom_count = IntOutput("OGR_G_GetGeometryCount", argtypes=[c_void_p])
get_geom_name = ConstStringOutput(
    "OGR_G_GetGeometryName", argtypes=[c_void_p], decoding="ascii"
)
get_geom_type = IntOutput("OGR_G_GetGeometryType", argtypes=[c_void_p])
get_point_count = IntOutput("OGR_G_GetPointCount", argtypes=[c_void_p])
get_point = VoidOutput(
    "OGR_G_GetPointZM",
    argtypes=[
        c_void_p,
        c_int,
        POINTER(c_double),
        POINTER(c_double),
        POINTER(c_double),
        POINTER(c_double),
    ],
    errcheck=False,
)
geom_close_rings = VoidOutput("OGR_G_CloseRings", argtypes=[c_void_p], errcheck=False)

# Topology routines.
ogr_contains = TopologyFunc("OGR_G_Contains")
ogr_crosses = TopologyFunc("OGR_G_Crosses")
ogr_disjoint = TopologyFunc("OGR_G_Disjoint")
ogr_equals = TopologyFunc("OGR_G_Equals")
ogr_intersects = TopologyFunc("OGR_G_Intersects")
ogr_overlaps = TopologyFunc("OGR_G_Overlaps")
ogr_touches = TopologyFunc("OGR_G_Touches")
ogr_within = TopologyFunc("OGR_G_Within")

# Transformation routines.
geom_transform = VoidOutput("OGR_G_Transform", argtypes=[c_void_p, c_void_p])
geom_transform_to = VoidOutput("OGR_G_TransformTo", argtypes=[c_void_p, c_void_p])

# For retrieving the envelope of the geometry.
get_envelope = EnvFunc("OGR_G_GetEnvelope", argtypes=[c_void_p, POINTER(OGREnvelope)])
