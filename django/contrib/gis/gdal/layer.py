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
    get_next_feature, reset_reading, test_capability
from django.contrib.gis.gdal.prototypes.srs import clone_srs

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_L_* routines are relevant here.
class Layer(object):
    "A class that wraps an OGR Layer, needs to be instantiated from a DataSource object."

    #### Python 'magic' routines ####
    def __init__(self, layer_ptr, ds):
        """
        Initializes on an OGR C pointer to the Layer and the `DataSource` object
        that owns this layer.  The `DataSource` object is required so that a 
        reference to it is kept with this Layer.  This prevents garbage 
        collection of the `DataSource` while this Layer is still active.
        """
        self._ptr = None # Initially NULL
        if not layer_ptr:
            raise OGRException('Cannot create Layer, invalid pointer given')
        self._ptr = layer_ptr
        self._ds = ds
        self._ldefn = get_layer_defn(self._ptr)
        # Does the Layer support random reading?
        self._random_read = self.test_capability('RandomRead')

    def __getitem__(self, index):
        "Gets the Feature at the specified index."
        if isinstance(index, (int, long)):
            # An integer index was given -- we cannot do a check based on the
            # number of features because the beginning and ending feature IDs
            # are not guaranteed to be 0 and len(layer)-1, respectively.
            if index < 0: raise OGRIndexError('Negative indices are not allowed on OGR Layers.')
            return self._make_feature(index)
        elif isinstance(index, slice):
            # A slice was given
            start, stop, stride = index.indices(self.num_feat)
            return [self._make_feature(fid) for fid in xrange(start, stop, stride)]
        else:
            raise TypeError('Integers and slices may only be used when indexing OGR Layers.')

    def __iter__(self):
        "Iterates over each Feature in the Layer."
        # ResetReading() must be called before iteration is to begin.
        reset_reading(self._ptr)
        for i in xrange(self.num_feat):
            yield Feature(get_next_feature(self._ptr), self._ldefn)

    def __len__(self):
        "The length is the number of features."
        return self.num_feat

    def __str__(self):
        "The string name of the layer."
        return self.name

    def _make_feature(self, feat_id):
        """
        Helper routine for __getitem__ that constructs a Feature from the given
        Feature ID.  If the OGR Layer does not support random-access reading,
        then each feature of the layer will be incremented through until the
        a Feature is found matching the given feature ID.
        """
        if self._random_read:
            # If the Layer supports random reading, return.
            try:
                return Feature(get_feature(self._ptr, feat_id), self._ldefn)
            except OGRException:
                pass
        else:
            # Random access isn't supported, have to increment through
            # each feature until the given feature ID is encountered.
            for feat in self:
                if feat.fid == feat_id: return feat
        # Should have returned a Feature, raise an OGRIndexError.    
        raise OGRIndexError('Invalid feature id: %s.' % feat_id)

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

    def test_capability(self, capability):
        """
        Returns a bool indicating whether the this Layer supports the given
        capability (a string).  Valid capability strings include:
          'RandomRead', 'SequentialWrite', 'RandomWrite', 'FastSpatialFilter',
          'FastFeatureCount', 'FastGetExtent', 'CreateField', 'Transactions',
          'DeleteFeature', and 'FastSetNextByIndex'.
        """
        return bool(test_capability(self._ptr, capability))
