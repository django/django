# Needed ctypes routines
from ctypes import c_int, c_long, c_void_p, byref, string_at

# The GDAL C Library
from django.contrib.gis.gdal.libgdal import lgdal

# Other GDAL imports.
from django.contrib.gis.gdal.Envelope import Envelope, OGREnvelope
from django.contrib.gis.gdal.Feature import Feature
from django.contrib.gis.gdal.OGRGeometry import OGRGeomType
from django.contrib.gis.gdal.OGRError import OGRException, check_err
from django.contrib.gis.gdal.SpatialReference import SpatialReference

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_L_* routines are relevant here.

get_srs = lgdal.OGR_L_GetSpatialRef
get_srs.restype = c_void_p
get_srs.argtypes = [c_void_p]

class Layer(object):
    "A class that wraps an OGR Layer, needs to be instantiated from a DataSource object."

    _layer = 0 # Initially NULL

    #### Python 'magic' routines ####
    def __init__(self, l):
        "Needs a C pointer (Python/ctypes integer) in order to initialize."
        if not l:
            raise OGRException, 'Cannot create Layer, invalid pointer given'
        self._layer = l
        self._ldefn = lgdal.OGR_L_GetLayerDefn(l)

    def __getitem__(self, index):
        "Gets the Feature at the specified index."
        def make_feature(offset):
            return Feature(lgdal.OGR_L_GetFeature(self._layer,
                                                  c_long(offset)))
        end = self.num_feat
        if not isinstance(index, (slice, int)):
            raise TypeError
        if isinstance(index,int):
            if index < 0:
                index = end - index
            if index < 0 or index >= self.num_feat:
                raise IndexError, 'index out of range'
            yield make_feature(index)
        else: #isinstance(index,slice)
            start, stop, stride = index.indices(end)
            for offset in xrange(start,stop,stride):
                yield make_feature(offset)

    def __iter__(self):
        "Iterates over each Feature in the Layer."
        return self.__getitem__(slice(self.num_feat))

    def __len__(self):
        "The length is the number of features."
        return self.num_feat

    def __str__(self):
        "The string name of the layer."
        return self.name

    #### Layer properties ####
    @property
    def extent(self):
        "Returns the extent (an Envelope) of this layer."
        env = OGREnvelope()
        check_err(lgdal.OGR_L_GetExtent(self._layer, byref(env), c_int(1)))
        return Envelope(env)

    @property
    def name(self):
        "Returns the name of this layer in the Data Source."
        return string_at(lgdal.OGR_FD_GetName(self._ldefn))

    @property
    def num_feat(self, force=1):
        "Returns the number of features in the Layer."
        return lgdal.OGR_L_GetFeatureCount(self._layer, c_int(force))

    @property
    def num_fields(self):
        "Returns the number of fields in the Layer."
        return lgdal.OGR_FD_GetFieldCount(self._ldefn)

    @property
    def geom_type(self):
        "Returns the geometry type (OGRGeomType) of the Layer."
        return OGRGeomType(lgdal.OGR_FD_GetGeomType(self._ldefn))

    @property
    def srs(self):
        "Returns the Spatial Reference used in this Layer."
        ptr = lgdal.OGR_L_GetSpatialRef(self._layer)
        if ptr:
            srs = SpatialReference(lgdal.OSRClone(ptr), 'ogr')
        else:
            return None

    @property
    def fields(self):
        "Returns a list of the fields available in this Layer."
        return [ string_at(lgdal.OGR_Fld_GetNameRef(lgdal.OGR_FD_GetFieldDefn(self._ldefn, i)))
                 for i in xrange(self.num_fields) ]
    
