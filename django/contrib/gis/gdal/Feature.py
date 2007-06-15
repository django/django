# types and ctypes
from types import StringType
from ctypes import c_char_p, c_int, string_at

# The GDAL C library, OGR exception, and the Field object
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.gdal.OGRError import OGRException
from django.contrib.gis.gdal.Field import Field
from django.contrib.gis.gdal.OGRGeometry import OGRGeometry, OGRGeomType

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_F_* routines are relevant here.
class Feature(object):
    "A class that wraps an OGR Feature, needs to be instantiated from a Layer object."

    _feat = 0 # Initially NULL

    #### Python 'magic' routines ####
    def __init__(self, f):
        "Needs a C pointer (Python integer in ctypes) in order to initialize."
        if not f:
            raise OGRException, 'Cannot create OGR Feature, invalid pointer given.'
        self._feat = f
        self._fdefn = lgdal.OGR_F_GetDefnRef(f)

    def __del__(self):
        "Releases a reference to this object."
        if self._fdefn: lgdal.OGR_FD_Release(self._fdefn)

    def __getitem__(self, index):
        "Gets the Field at the specified index."
        if isinstance(index, StringType):
            i = self.index(index)
        else:
            if index < 0 or index > self.num_fields:
                raise IndexError, 'index out of range'
            i = index
        return Field(lgdal.OGR_F_GetFieldDefnRef(self._feat, c_int(i)),
                     string_at(lgdal.OGR_F_GetFieldAsString(self._feat, c_int(i))))

    def __iter__(self):
        "Iterates over each field in the Feature."
        for i in xrange(self.num_fields):
            yield self.__getitem__(i)

    def __len__(self):
        "Returns the count of fields in this feature."
        return self.num_fields
        
    def __str__(self):
        "The string name of the feature."
        return 'Feature FID %d in Layer<%s>' % (self.fid, self.layer_name)

    def __eq__(self, other):
        "Does equivalence testing on the features."
        if lgdal.OGR_F_Equal(self._feat, other._feat):
            return True
        else:
            return False

    #### Feature Properties ####
    @property
    def fid(self):
        "Returns the feature identifier."
        return lgdal.OGR_F_GetFID(self._feat)
        
    @property
    def layer_name(self):
        "Returns the name of the layer for the feature."
        return string_at(lgdal.OGR_FD_GetName(self._fdefn))

    @property
    def num_fields(self):
        "Returns the number of fields in the Feature."
        return lgdal.OGR_F_GetFieldCount(self._feat)

    @property
    def fields(self):
        "Returns a list of fields in the Feature."
        return [ string_at(lgdal.OGR_Fld_GetNameRef(lgdal.OGR_FD_GetFieldDefn(self._fdefn, i)))
                 for i in xrange(self.num_fields) ]
    @property
    def geom(self):
        "Returns the OGR Geometry for this Feature."
        # A clone is used, so destruction of the Geometry won't bork the Feature.
        return OGRGeometry(lgdal.OGR_G_Clone(lgdal.OGR_F_GetGeometryRef(self._feat)))

    @property
    def geom_type(self):
        "Returns the OGR Geometry Type for this Feture."
        return OGRGeomType(lgdal.OGR_FD_GetGeomType(self._fdefn))
    
    #### Feature Methods ####
    def index(self, field_name):
        "Returns the index of the given field name."
        i = lgdal.OGR_F_GetFieldIndex(self._feat, c_char_p(field_name))
        if i < 0: raise IndexError, 'invalid OFT field name given: "%s"' % field_name
        return i

    def clone(self):
        "Clones this Feature."
        return Feature(lgdal.OGR_F_Clone(self._feat))
