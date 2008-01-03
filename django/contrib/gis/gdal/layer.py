# Needed ctypes routines
from ctypes import byref

# Other GDAL imports.
from django.contrib.gis.gdal.envelope import Envelope, OGREnvelope
from django.contrib.gis.gdal.error import OGRException, OGRIndexError, SRSException
from django.contrib.gis.gdal.feature import Feature
from django.contrib.gis.gdal.field import FIELD_CLASSES
from django.contrib.gis.gdal.geometries import OGRGeomType
from django.contrib.gis.gdal.srs import SpatialReference

# GDAL ctypes function prototypes.
from django.contrib.gis.gdal.prototypes.ds import \
    get_extent, get_fd_geom_type, get_fd_name, get_feature, get_feature_count, \
    get_field_count, get_field_defn, get_field_name, get_field_precision, \
    get_field_width, get_field_type, get_layer_defn, get_layer_srs, \
    get_next_feature, reset_reading
from django.contrib.gis.gdal.prototypes.srs import clone_srs

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_L_* routines are relevant here.
class Layer(object):
    "A class that wraps an OGR Layer, needs to be instantiated from a DataSource object."

    #### Python 'magic' routines ####
    def __init__(self, layer_ptr):
        "Needs a C pointer (Python/ctypes integer) in order to initialize."
        self._ptr = None # Initially NULL
        if not layer_ptr:
            raise OGRException('Cannot create Layer, invalid pointer given')
        self._ptr = layer_ptr
        self._ldefn = get_layer_defn(self._ptr)

    def __getitem__(self, index):
        "Gets the Feature at the specified index."
        if not isinstance(index, (slice, int)):
            raise TypeError
        end = self.num_feat
        if isinstance(index,int):
            # An integer index was given
            if index < 0:
                index = end - index
            if index < 0 or index >= self.num_feat:
                raise OGRIndexError('index out of range')
            return self._make_feature(index)
        else: 
            # A slice was given
            start, stop, stride = index.indices(end)
            return [self._make_feature(offset) for offset in range(start,stop,stride)]

    def __iter__(self):
        "Iterates over each Feature in the Layer."
        # ResetReading() must be called before iteration is to begin.
        reset_reading(self._ptr)
        for i in range(self.num_feat):
            yield Feature(get_next_feature(self._ptr), self._ldefn)

    def __len__(self):
        "The length is the number of features."
        return self.num_feat

    def __str__(self):
        "The string name of the layer."
        return self.name

    def _make_feature(self, offset):
        "Helper routine for __getitem__ that makes a feature from an offset."
        return Feature(get_feature(self._ptr, offset), self._ldefn)

    #### Layer properties ####
    @property
    def extent(self):
        "Returns the extent (an Envelope) of this layer."
        env = OGREnvelope()
        get_extent(self._ptr, byref(env), 1)
        return Envelope(env)

    @property
    def name(self):
        "Returns the name of this layer in the Data Source."
        return get_fd_name(self._ldefn)

    @property
    def num_feat(self, force=1):
        "Returns the number of features in the Layer."
        return get_feature_count(self._ptr, force)

    @property
    def num_fields(self):
        "Returns the number of fields in the Layer."
        return get_field_count(self._ldefn)

    @property
    def geom_type(self):
        "Returns the geometry type (OGRGeomType) of the Layer."
        return OGRGeomType(get_fd_geom_type(self._ldefn))

    @property
    def srs(self):
        "Returns the Spatial Reference used in this Layer."
        try:
            ptr = get_layer_srs(self._ptr)
            return SpatialReference(clone_srs(ptr))
        except SRSException:
            return None

    @property
    def fields(self):
        """
        Returns a list of string names corresponding to each of the Fields
        available in this Layer.
        """
        return [get_field_name(get_field_defn(self._ldefn, i)) 
                for i in xrange(self.num_fields) ]
    
    @property
    def field_types(self):
        """
        Returns a list of the types of fields in this Layer.  For example,
        the list [OFTInteger, OFTReal, OFTString] would be returned for
        an OGR layer that had an integer, a floating-point, and string
        fields.
        """
        return [FIELD_CLASSES[get_field_type(get_field_defn(self._ldefn, i))]
                for i in xrange(self.num_fields)]

    @property 
    def field_widths(self):
        "Returns a list of the maximum field widths for the features."
        return [get_field_width(get_field_defn(self._ldefn, i))
                for i in xrange(self.num_fields)]

    @property 
    def field_precisions(self):
        "Returns the field precisions for the features."
        return [get_field_precision(get_field_defn(self._ldefn, i))
                for i in xrange(self.num_fields)]

    #### Layer Methods ####
    def get_fields(self, field_name):
        """
        Returns a list containing the given field name for every Feature
        in the Layer.
        """
        if not field_name in self.fields:
            raise OGRException('invalid field name: %s' % field_name)
        return [feat.get(field_name) for feat in self]

    def get_geoms(self, geos=False):
        """
        Returns a list containing the OGRGeometry for every Feature in
        the Layer.
        """
        if geos:
            from django.contrib.gis.geos import GEOSGeometry
            return [GEOSGeometry(feat.geom.wkb) for feat in self]
        else:
            return [feat.geom for feat in self]
