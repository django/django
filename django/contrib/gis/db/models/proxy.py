"""
  The GeometryProxy object, allows for lazy-geometries.  The proxy uses
   Python descriptors for instantiating and setting GEOS Geometry objects
   corresponding to geographic model fields.

  Thanks to Robert Coup for providing this functionality (see #4322).
"""

from types import NoneType, StringType, UnicodeType
from django.contrib.gis.geos import GEOSGeometry, GEOSException 

# TODO: docstrings
class GeometryProxy(object): 
    def __init__(self, field): 
        "Proxy initializes on the given GeometryField."
        self._field = field 
     
    def __get__(self, obj, type=None): 
        # Getting the value of the field.
        geom_value = obj.__dict__[self._field.attname] 

        if isinstance(geom_value, GEOSGeometry): 
            # If the value of the field is None, or is already a GEOS Geometry
            #  no more work is needed.
            geom = geom_value
        elif (geom_value is None) or (geom_value==''):
            geom = None
        else: 
            # Otherwise, a GEOSGeometry object is built using the field's contents,
            #  and the model's corresponding attribute is set.
            geom = GEOSGeometry(geom_value)
            setattr(obj, self._field.attname, geom) 
        return geom 
     
    def __set__(self, obj, value): 
        if isinstance(value, GEOSGeometry) and (value.geom_type.upper() == self._field._geom):
            # Getting set with GEOS Geometry; geom_type must match that of the field.

            # If value's SRID is not set, setting it to the field's SRID.
            if value.srid is None: value.srid = self._field._srid
        elif isinstance(value, (NoneType, StringType, UnicodeType)):
            # Getting set with None, WKT, or HEX
            pass
        else:
            raise TypeError, 'cannot set %s GeometryProxy with value of type: %s' % (self._field._geom, type(value))
        obj.__dict__[self._field.attname] = value 
        return value 
