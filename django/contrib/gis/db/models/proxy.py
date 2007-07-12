"""
  The GeometryProxy object, allows for lazy-geometries.

  Thanks to Robert Coup for providing this functionality (see #4322).
"""

# GEOS Routines 
from django.contrib.gis.geos import GEOSGeometry, GEOSException 

# TODO: docstrings & comments
class GeometryProxy(object): 
    def __init__(self, field): 
        self._field = field 
     
    def __get__(self, obj, type=None): 
        geom_value = obj.__dict__[self._field.attname] 
        if (geom_value is None) or (isinstance(geom_value, GEOSGeometry)): 
            geom = geom_value 
        else: 
            geom = GEOSGeometry(geom_value) 
            setattr(obj, self._field.attname, geom) 
        return geom 
     
    def __set__(self, obj, value): 
        if isinstance(value, GEOSGeometry): 
            if value and ((value.srid is None) and (self._field._srid is not None)): 
                value.set_srid(self._field._srid) 
     
        obj.__dict__[self._field.attname] = value 
        return value 
