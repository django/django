"""
 The GeometryProxy object, allows for lazy-geometries.  The proxy uses
 Python descriptors for instantiating and setting Geometry objects
 corresponding to geographic model fields.

 Thanks to Robert Coup for providing this functionality (see #4322).
"""

from types import NoneType, StringType, UnicodeType

class GeometryProxy(object): 
    def __init__(self, klass, field): 
        """
        Proxy initializes on the given Geometry class (not an instance) and 
        the GeometryField.
        """
        self._field = field 
        self._klass = klass
     
    def __get__(self, obj, type=None): 
        """
        This accessor retrieves the geometry, initializing it using the geometry
        class specified during initialization and the HEXEWKB value of the field.  
        Currently, only GEOS or OGR geometries are supported.
        """
        # Getting the value of the field.
        geom_value = obj.__dict__[self._field.attname] 
        
        if isinstance(geom_value, self._klass): 
            geom = geom_value
        elif (geom_value is None) or (geom_value==''):
            geom = None
        else: 
            # Otherwise, a Geometry object is built using the field's contents,
            # and the model's corresponding attribute is set.
            geom = self._klass(geom_value)
            setattr(obj, self._field.attname, geom) 
        return geom 
     
    def __set__(self, obj, value):
        """
        This accessor sets the proxied geometry with the geometry class
        specified during initialization.  Values of None, HEXEWKB, or WKT may
        be used to set the geometry as well.
        """
        # The OGC Geometry type of the field.
        gtype = self._field._geom
        
        # The geometry type must match that of the field -- unless the
        # general GeometryField is used.
        if isinstance(value, self._klass) and (str(value.geom_type).upper() == gtype or gtype == 'GEOMETRY'):
            # Assigning the SRID to the geometry.
            if value.srid is None: value.srid = self._field._srid
        elif isinstance(value, (NoneType, StringType, UnicodeType)):
            # Set with None, WKT, or HEX
            pass
        else:
            raise TypeError('cannot set %s GeometryProxy with value of type: %s' % (obj.__class__.__name__, type(value)))

        # Setting the objects dictionary with the value, and returning.
        obj.__dict__[self._field.attname] = value 
        return value 
