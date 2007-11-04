from ctypes import string_at
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.gdal.error import OGRException

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_Fld_* routines are relevant here.
class Field(object):
    "A class that wraps an OGR Field, needs to be instantiated from a Feature object."

    #### Python 'magic' routines ####
    def __init__(self, fld, val=''):
        "Needs a C pointer (Python integer in ctypes) in order to initialize."
        self._fld = None # Initially NULL

        if not fld:
            raise OGRException('Cannot create OGR Field, invalid pointer given.')
        self._fld = fld
        self._val = val

        # Setting the class depending upon the OGR Field Type (OFT)
        self.__class__ = FIELD_CLASSES[self.type]

    def __str__(self):
        "Returns the string representation of the Field."
        return '%s (%s)' % (self.name, self.value)

    #### Field Properties ####
    @property
    def name(self):
        "Returns the name of the field."
        return string_at(lgdal.OGR_Fld_GetNameRef(self._fld))

    @property
    def type(self):
        "Returns the type of this field."
        return lgdal.OGR_Fld_GetType(self._fld)

    @property
    def value(self):
        "Returns the value of this type of field."
        return self._val

# The Field sub-classes for each OGR Field type.
class OFTInteger(Field):
    @property
    def value(self):
        "Returns an integer contained in this field."
        try:
            return int(self._val)
        except ValueError:
            return None
class OFTIntegerList(Field): pass

class OFTReal(Field):
    @property
    def value(self):
        "Returns a float contained in this field."
        try:
            return float(self._val)
        except ValueError:
            return None
class OFTRealList(Field): pass

class OFTString(Field):
    def __str__(self):
        return '%s ("%s")' % (self.name, self.value)
    
class OFTStringList(Field): pass
class OFTWideString(Field): pass
class OFTWideStringList(Field): pass
class OFTBinary(Field): pass
class OFTDate(Field): pass
class OFTTime(Field): pass
class OFTDateTime(Field): pass

# Class mapping dictionary for OFT Types
FIELD_CLASSES = { 0 : OFTInteger,
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
