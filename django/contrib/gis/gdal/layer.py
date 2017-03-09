from contextlib import suppress
from ctypes import byref, c_double

from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.envelope import Envelope, OGREnvelope
from django.contrib.gis.gdal.error import (
    GDALException, OGRIndexError, SRSException,
)
from django.contrib.gis.gdal.feature import Feature
from django.contrib.gis.gdal.field import OGRFieldTypes
from django.contrib.gis.gdal.geometries import OGRGeometry
from django.contrib.gis.gdal.geomtype import OGRGeomType
from django.contrib.gis.gdal.prototypes import (
    ds as capi, geom as geom_api, srs as srs_api,
)
from django.contrib.gis.gdal.srs import SpatialReference
from django.utils.encoding import force_bytes, force_text


# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr__api_8h.html
#
# The OGR_L_* routines are relevant here.
class Layer(GDALBase):
    "A class that wraps an OGR Layer, needs to be instantiated from a DataSource object."

    def __init__(self, layer_ptr, ds):
        """
        Initialize on an OGR C pointer to the Layer and the `DataSource` object
        that owns this layer.  The `DataSource` object is required so that a
        reference to it is kept with this Layer.  This prevents garbage
        collection of the `DataSource` while this Layer is still active.
        """
        if not layer_ptr:
            raise GDALException('Cannot create Layer, invalid pointer given')
        self.ptr = layer_ptr
        self._ds = ds
        self._ldefn = capi.get_layer_defn(self._ptr)
        # Does the Layer support random reading?
        self._random_read = self.test_capability(b'RandomRead')

    def __getitem__(self, index):
        "Get the Feature at the specified index."
        if isinstance(index, int):
            # An integer index was given -- we cannot do a check based on the
            # number of features because the beginning and ending feature IDs
            # are not guaranteed to be 0 and len(layer)-1, respectively.
            if index < 0:
                raise OGRIndexError('Negative indices are not allowed on OGR Layers.')
            return self._make_feature(index)
        elif isinstance(index, slice):
            # A slice was given
            start, stop, stride = index.indices(self.num_feat)
            return [self._make_feature(fid) for fid in range(start, stop, stride)]
        else:
            raise TypeError('Integers and slices may only be used when indexing OGR Layers.')

    def __iter__(self):
        "Iterate over each Feature in the Layer."
        # ResetReading() must be called before iteration is to begin.
        capi.reset_reading(self._ptr)
        for i in range(self.num_feat):
            yield Feature(capi.get_next_feature(self._ptr), self)

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
            with suppress(GDALException):
                return Feature(capi.get_feature(self.ptr, feat_id), self)
        else:
            # Random access isn't supported, have to increment through
            # each feature until the given feature ID is encountered.
            for feat in self:
                if feat.fid == feat_id:
                    return feat
        # Should have returned a Feature, raise an OGRIndexError.
        raise OGRIndexError('Invalid feature id: %s.' % feat_id)

    # #### Layer properties ####
    @property
    def extent(self):
        "Return the extent (an Envelope) of this layer."
        env = OGREnvelope()
        capi.get_extent(self.ptr, byref(env), 1)
        return Envelope(env)

    @property
    def name(self):
        "Return the name of this layer in the Data Source."
        name = capi.get_fd_name(self._ldefn)
        return force_text(name, self._ds.encoding, strings_only=True)

    @property
    def num_feat(self, force=1):
        "Return the number of features in the Layer."
        return capi.get_feature_count(self.ptr, force)

    @property
    def num_fields(self):
        "Return the number of fields in the Layer."
        return capi.get_field_count(self._ldefn)

    @property
    def geom_type(self):
        "Return the geometry type (OGRGeomType) of the Layer."
        return OGRGeomType(capi.get_fd_geom_type(self._ldefn))

    @property
    def srs(self):
        "Return the Spatial Reference used in this Layer."
        try:
            ptr = capi.get_layer_srs(self.ptr)
            return SpatialReference(srs_api.clone_srs(ptr))
        except SRSException:
            return None

    @property
    def fields(self):
        """
        Return a list of string names corresponding to each of the Fields
        available in this Layer.
        """
        return [force_text(capi.get_field_name(capi.get_field_defn(self._ldefn, i)),
                           self._ds.encoding, strings_only=True)
                for i in range(self.num_fields)]

    @property
    def field_types(self):
        """
        Return a list of the types of fields in this Layer.  For example,
        return the list [OFTInteger, OFTReal, OFTString] for an OGR layer that
        has an integer, a floating-point, and string fields.
        """
        return [OGRFieldTypes[capi.get_field_type(capi.get_field_defn(self._ldefn, i))]
                for i in range(self.num_fields)]

    @property
    def field_widths(self):
        "Return a list of the maximum field widths for the features."
        return [capi.get_field_width(capi.get_field_defn(self._ldefn, i))
                for i in range(self.num_fields)]

    @property
    def field_precisions(self):
        "Return the field precisions for the features."
        return [capi.get_field_precision(capi.get_field_defn(self._ldefn, i))
                for i in range(self.num_fields)]

    def _get_spatial_filter(self):
        try:
            return OGRGeometry(geom_api.clone_geom(capi.get_spatial_filter(self.ptr)))
        except GDALException:
            return None

    def _set_spatial_filter(self, filter):
        if isinstance(filter, OGRGeometry):
            capi.set_spatial_filter(self.ptr, filter.ptr)
        elif isinstance(filter, (tuple, list)):
            if not len(filter) == 4:
                raise ValueError('Spatial filter list/tuple must have 4 elements.')
            # Map c_double onto params -- if a bad type is passed in it
            # will be caught here.
            xmin, ymin, xmax, ymax = map(c_double, filter)
            capi.set_spatial_filter_rect(self.ptr, xmin, ymin, xmax, ymax)
        elif filter is None:
            capi.set_spatial_filter(self.ptr, None)
        else:
            raise TypeError('Spatial filter must be either an OGRGeometry instance, a 4-tuple, or None.')

    spatial_filter = property(_get_spatial_filter, _set_spatial_filter)

    # #### Layer Methods ####
    def get_fields(self, field_name):
        """
        Return a list containing the given field name for every Feature
        in the Layer.
        """
        if field_name not in self.fields:
            raise GDALException('invalid field name: %s' % field_name)
        return [feat.get(field_name) for feat in self]

    def get_geoms(self, geos=False):
        """
        Return a list containing the OGRGeometry for every Feature in
        the Layer.
        """
        if geos:
            from django.contrib.gis.geos import GEOSGeometry
            return [GEOSGeometry(feat.geom.wkb) for feat in self]
        else:
            return [feat.geom for feat in self]

    def test_capability(self, capability):
        """
        Return a bool indicating whether the this Layer supports the given
        capability (a string).  Valid capability strings include:
          'RandomRead', 'SequentialWrite', 'RandomWrite', 'FastSpatialFilter',
          'FastFeatureCount', 'FastGetExtent', 'CreateField', 'Transactions',
          'DeleteFeature', and 'FastSetNextByIndex'.
        """
        return bool(capi.test_capability(self.ptr, force_bytes(capability)))
