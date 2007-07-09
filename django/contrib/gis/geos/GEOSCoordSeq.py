from django.contrib.gis.geos.libgeos import lgeos
from django.contrib.gis.geos.GEOSError import GEOSException, GEOSGeometryIndexError
from ctypes import c_double, c_int, c_uint, byref

"""
  This module houses the GEOSCoordSeq object, and is used internally
  by GEOSGeometry to house the actual coordinates of the Point,
  LineString, and LinearRing geometries.
"""

class GEOSCoordSeq(object):
    "The internal representation of a list of coordinates inside a Geometry."

    #### Python 'magic' routines ####
    def __init__(self, ptr, z=False):
        "Initializes from a GEOS pointer."
        self._ptr = ptr
        self._z = z

    def __iter__(self):
        "Iterates over each point in the coordinate sequence."
        for i in xrange(self.size):
            yield self.__getitem__(i)

    def __len__(self):
        "Returns the number of points in the coordinate sequence."
        return int(self.size)

    def __str__(self):
        "The string representation of the coordinate sequence."
        return str(self.tuple)

    def __getitem__(self, index):
        "Can use the index [] operator to get coordinate sequence at an index."
        coords = [self.getX(index), self.getY(index)]
        if self.dims == 3 and self._z:
            coords.append(self.getZ(index))
        return tuple(coords)

    def __setitem__(self, index, value):
        "Can use the index [] operator to set coordinate sequence at an index."
        if self.dims == 3 and self._z:
            n_args = 3
            set_3d = True
        else:
            n_args = 2
            set_3d = False
        if len(value) != n_args:
            raise TypeError, 'Dimension of value does not match.'
        self.setX(index, value[0])
        self.setY(index, value[1])
        if set_3d: self.setZ(index, value[2])

    #### Internal Routines ####
    def _checkindex(self, index):
        "Checks the index."
        sz = self.size
        if (sz < 1) or (index < 0) or (index >= sz):
            raise GEOSGeometryIndexError, 'invalid GEOS Geometry index: %s' % str(index)

    def _checkdim(self, dim):
        "Checks the given dimension."
        if dim < 0 or dim > 2:
            raise GEOSException, 'invalid ordinate dimension "%d"' % dim

    #### Ordinate getting and setting routines ####
    def getOrdinate(self, dimension, index):
        "Gets the value for the given dimension and index."
        self._checkindex(index)
        self._checkdim(dimension)

        # Wrapping the dimension, index
        dim = c_uint(dimension)
        idx = c_uint(index)

        # 'd' is the value of the point, passed in by reference
        d = c_double()
        status = lgeos.GEOSCoordSeq_getOrdinate(self._ptr(), idx, dim, byref(d))
        if status == 0:
            raise GEOSException, 'could not retrieve %th ordinate at index: %s' % (str(dimension), str(index))
        return d.value

    def setOrdinate(self, dimension, index, value):
        "Sets the value for the given dimension and index."
        self._checkindex(index)
        self._checkdim(dimension)

        # Wrapping the dimension, index
        dim = c_uint(dimension)
        idx = c_uint(index)

        # Setting the ordinate
        status = lgeos.GEOSCoordSeq_setOrdinate(self._ptr(), idx, dim, c_double(value))
        if status == 0:
            raise GEOSException, 'Could not set the ordinate for (dim, index): (%d, %d)' % (dimension, index)

    def getX(self, index):
        "Get the X value at the index."
        return self.getOrdinate(0, index)

    def setX(self, index, value):
        "Set X with the value at the given index."
        self.setOrdinate(0, index, value)

    def getY(self, index):
        "Get the Y value at the given index."
        return self.getOrdinate(1, index)

    def setY(self, index, value):
        "Set Y with the value at the given index."
        self.setOrdinate(1, index, value)

    def getZ(self, index):
        "Get Z with the value at the given index."
        return self.getOrdinate(2, index)

    def setZ(self, index, value):
        "Set Z with the value at the given index."
        self.setOrdinate(2, index, value)

    ### Dimensions ###
    @property
    def size(self):
        "Returns the size of this coordinate sequence."
        n = c_uint(0)
        status = lgeos.GEOSCoordSeq_getSize(self._ptr(), byref(n))
        if status == 0:
            raise GEOSException, 'Could not get CoordSeq size.'
        return n.value

    @property
    def dims(self):
        "Returns the dimensions of this coordinate sequence."
        n = c_uint(0)
        status = lgeos.GEOSCoordSeq_getDimensions(self._ptr(), byref(n))
        if status == 0:
            raise GEOSException, 'Could not get CoordSeq dimensions.'
        return n.value

    @property
    def hasz(self):
        "Inherits this from the parent geometry."
        return self._z

    ### Other Methods ###
    @property
    def clone(self):
        "Clones this coordinate sequence."
        pass

    @property
    def tuple(self):
        "Returns a tuple version of this coordinate sequence."
        n = self.size
        if n == 1:
            return self.__getitem__(0)
        else:
            return tuple(self.__getitem__(i) for i in xrange(n))

# ctypes prototype for the Coordinate Sequence creation factory
create_cs = lgeos.GEOSCoordSeq_create
create_cs.argtypes = [c_uint, c_uint]
