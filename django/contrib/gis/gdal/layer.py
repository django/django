# Needed ctypes routines
from ctypes import c_int, c_long, c_void_p, byref, string_at

# The GDAL C Library
from django.contrib.gis.gdal.libgdal import lgdal

# Other GDAL imports.
from django.contrib.gis.gdal.envelope import Envelope, OGREnvelope
from django.contrib.gis.gdal.feature import Feature
from django.contrib.gis.gdal.geometries import OGRGeomType
from django.contrib.gis.gdal.error import OGRException, check_err
from django.contrib.gis.gdal.srs import SpatialReference

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_L_* routines are relevant here.

# function prototype for obtaining the spatial reference system
get_srs = lgdal.OGR_L_GetSpatialRef
get_srs.restype = c_void_p
get_srs.argtypes = [c_void_p]

class Layer(object):
    "A class that wraps an OGR Layer, needs to be instantiated from a DataSource object."

    #### Python 'magic' routines ####
    def __init__(self, l):
        "Needs a C pointer (Python/ctypes integer) in order to initialize."
        self._layer = 0 # Initially NULL
        self._ldefn = 0
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
            # An integer index was given
            if index < 0:
                index = end - index
            if index < 0 or index >= self.num_feat:
                raise IndexError, 'index out of range'
            return make_feature(index)
        else: 
            # A slice was given
            start, stop, stride = index.indices(end)
            return [make_feature(offset) for offset in range(start,stop,stride)]

    def __iter__(self):
        "Iterates over each Feature in the Layer."
        #TODO: is OGR's GetNextFeature faster here?
        for i in range(self.num_feat):
            yield self.__getitem__(i)

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
            return SpatialReference(lgdal.OSRClone(ptr), 'ogr')
        else:
            return None

    @property
    def fields(self):
        "Returns a list of the fields available in this Layer."
        return [ string_at(lgdal.OGR_Fld_GetNameRef(lgdal.OGR_FD_GetFieldDefn(self._ldefn, i)))
                 for i in xrange(self.num_fields) ]
    
    #### Layer Methods ####
    def get_fields(self, field_name):
        """Returns a list containing the given field name for every Feature
        in the Layer."""
        if not field_name in self.fields:
            raise OGRException, 'invalid field name: %s' % field_name
        return [feat.get(field_name) for feat in self]

    def get_geoms(self, geos=False):
        """Returns a list containing the OGRGeometry for every Feature in
        the Layer."""
        if geos:
            from django.contrib.gis.geos import fromstr
            return [fromstr(feat.geom.wkt) for feat in self]
        else:
            return [feat.geom for feat in self]
