from ctypes import byref, c_int
from datetime import date, datetime, time
from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.error import OGRException
from django.contrib.gis.gdal.prototypes import ds as capi

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_Fld_* routines are relevant here.
class Field(GDALBase):
    "A class that wraps an OGR Field, needs to be instantiated from a Feature object."

    #### Python 'magic' routines ####
    def __init__(self, feat, index):
        """
        Initializes on the feature pointer and the integer index of
        the field within the feature.
        """
        # Setting the feature pointer and index.
        self._feat = feat
        self._index = index
        
        # Getting the pointer for this field.
        fld_ptr = capi.get_feat_field_defn(feat, index)
        if not fld_ptr:
            raise OGRException('Cannot create OGR Field, invalid pointer given.')
        self.ptr = fld_ptr

        # Setting the class depending upon the OGR Field Type (OFT)
        self.__class__ = OGRFieldTypes[self.type]

        # OFTReal with no precision should be an OFTInteger.
        if isinstance(self, OFTReal) and self.precision == 0:
            self.__class__ = OFTInteger

    def __str__(self):
        "Returns the string representation of the Field."
        return str(self.value).strip()

    #### Field Methods ####
    def as_double(self):
        "Retrieves the Field's value as a double (float)."
        return capi.get_field_as_double(self._feat, self._index)

    def as_int(self):
        "Retrieves the Field's value as an integer."
        return capi.get_field_as_integer(self._feat, self._index)

    def as_string(self):
        "Retrieves the Field's value as a string."
        return capi.get_field_as_string(self._feat, self._index)

    def as_datetime(self):
        "Retrieves the Field's value as a tuple of date & time components."
        yy, mm, dd, hh, mn, ss, tz = [c_int() for i in range(7)]
        status = capi.get_field_as_datetime(self._feat, self._index, byref(yy), byref(mm), byref(dd),
                                            byref(hh), byref(mn), byref(ss), byref(tz))
        if status:
            return (yy, mm, dd, hh, mn, ss, tz)
        else:
            raise OGRException('Unable to retrieve date & time information from the field.')

    #### Field Properties ####
    @property
    def name(self):
        "Returns the name of this Field."
        return capi.get_field_name(self.ptr)

    @property
    def precision(self):
        "Returns the precision of this Field."
        return capi.get_field_precision(self.ptr)

    @property
    def type(self):
        "Returns the OGR type of this Field."
        return capi.get_field_type(self.ptr)

    @property
    def type_name(self):
        "Return the OGR field type name for this Field."
        return capi.get_field_type_name(self.type)

    @property
    def value(self):
        "Returns the value of this Field."
        # Default is to get the field as a string.
        return self.as_string()

    @property
    def width(self):
        "Returns the width of this Field."
        return capi.get_field_width(self.ptr)

### The Field sub-classes for each OGR Field type. ###
class OFTInteger(Field):
    @property
    def value(self):
        "Returns an integer contained in this field."
        return self.as_int()

    @property
    def type(self):
        """
        GDAL uses OFTReals to represent OFTIntegers in created
        shapefiles -- forcing the type here since the underlying field
        type may actually be OFTReal.
        """
        return 0

class OFTReal(Field):
    @property
    def value(self):
        "Returns a float contained in this field."
        return self.as_double()

# String & Binary fields, just subclasses
class OFTString(Field): pass
class OFTWideString(Field): pass
class OFTBinary(Field): pass

# OFTDate, OFTTime, OFTDateTime fields.
class OFTDate(Field):
    @property
    def value(self):
        "Returns a Python `date` object for the OFTDate field."
        try:
            yy, mm, dd, hh, mn, ss, tz = self.as_datetime()
            return date(yy.value, mm.value, dd.value)
        except (ValueError, OGRException):
            return None

class OFTDateTime(Field):
    @property
    def value(self):
        "Returns a Python `datetime` object for this OFTDateTime field."
        # TODO: Adapt timezone information.
        #  See http://lists.maptools.org/pipermail/gdal-dev/2006-February/007990.html
        #  The `tz` variable has values of: 0=unknown, 1=localtime (ambiguous), 
        #  100=GMT, 104=GMT+1, 80=GMT-5, etc.
        try:
            yy, mm, dd, hh, mn, ss, tz = self.as_datetime()
            return datetime(yy.value, mm.value, dd.value, hh.value, mn.value, ss.value)
        except (ValueError, OGRException):
            return None

class OFTTime(Field):
    @property
    def value(self):
        "Returns a Python `time` object for this OFTTime field."
        try:
            yy, mm, dd, hh, mn, ss, tz = self.as_datetime()
            return time(hh.value, mn.value, ss.value)
        except (ValueError, OGRException):
            return None

# List fields are also just subclasses
class OFTIntegerList(Field): pass
class OFTRealList(Field): pass
class OFTStringList(Field): pass
class OFTWideStringList(Field): pass

# Class mapping dictionary for OFT Types and reverse mapping.
OGRFieldTypes = { 0 : OFTInteger,
                  1 : OFTIntegerList,
                  2 : OFTReal,
                  3 : OFTRealList,
                  4 : OFTString,
                  5 : OFTStringList,
                  6 : OFTWideString,
                  7 : OFTWideStringList,
                  8 : OFTBinary,
                  9 : OFTDate,
                 10 : OFTTime,
                 11 : OFTDateTime,
                  }
ROGRFieldTypes = dict([(cls, num) for num, cls in OGRFieldTypes.items()])
