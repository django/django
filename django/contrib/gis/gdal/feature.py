# types and ctypes
from types import StringType
from ctypes import c_char_p, c_int, string_at

# The GDAL C library, OGR exception, and the Field object
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.gdal.error import OGRException, OGRIndexError
from django.contrib.gis.gdal.field import Field
from django.contrib.gis.gdal.geometries import OGRGeometry, OGRGeomType

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_F_* routines are relevant here.
class Feature(object):
    "A class that wraps an OGR Feature, needs to be instantiated from a Layer object."

    #### Python 'magic' routines ####
    def __init__(self, f):
        "Needs a C pointer (Python integer in ctypes) in order to initialize."
        self._feat = 0 # Initially NULL
        self._fdefn = 0 
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
                raise OGRIndexError, 'index out of range'
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
    def get(self, field):
        """
        Returns the value of the field, instead of an instance of the Field
         object.  May take a string of the field name or a Field object as
         parameters.
        """
        field_name = getattr(field, 'name', field)
        return self.__getitem__(field_name).value

    def index(self, field_name):
        "Returns the index of the given field name."
        i = lgdal.OGR_F_GetFieldIndex(self._feat, c_char_p(field_name))
        if i < 0: raise OGRIndexError, 'invalid OFT field name given: "%s"' % field_name
        return i

    def clone(self):
        "Clones this Feature."
        return Feature(lgdal.OGR_F_Clone(self._feat))
