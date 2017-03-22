from ctypes import c_uint

from django.contrib.gis import gdal
from django.contrib.gis.geos import prototypes as capi
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.geometry import GEOSGeometry


class Point(GEOSGeometry):
    _json_type = 'Point'
    _minlength = 2
    _maxlength = 3
    has_cs = True

    def __init__(self, x=None, y=None, z=None, srid=None):
        """
        The Point object may be initialized with either a tuple, or individual
        parameters.

        For example:
        >>> p = Point((5, 23))  # 2D point, passed in as a tuple
        >>> p = Point(5, 23, 8)  # 3D point, passed in with individual parameters
        """
        if x is None:
            coords = []
        elif isinstance(x, (tuple, list)):
            # Here a tuple or list was passed in under the `x` parameter.
            coords = x
        elif isinstance(x, (float, int)) and isinstance(y, (float, int)):
            # Here X, Y, and (optionally) Z were passed in individually, as parameters.
            if isinstance(z, (float, int)):
                coords = [x, y, z]
            else:
                coords = [x, y]
        else:
            raise TypeError('Invalid parameters given for Point initialization.')

        point = self._create_point(len(coords), coords)

        # Initializing using the address returned from the GEOS
        #  createPoint factory.
        super().__init__(point, srid=srid)

    def _ogr_ptr(self):
        return gdal.geometries.Point._create_empty() if self.empty else super()._ogr_ptr()

    @classmethod
    def _create_empty(cls):
        return cls._create_point(None, None)

    @classmethod
    def _create_point(cls, ndim, coords):
        """
        Create a coordinate sequence, set X, Y, [Z], and create point
        """
        if not ndim:
            return capi.create_point(None)

        if ndim < 2 or ndim > 3:
            raise TypeError('Invalid point dimension: %s' % ndim)

        cs = capi.create_cs(c_uint(1), c_uint(ndim))
        i = iter(coords)
        capi.cs_setx(cs, 0, next(i))
        capi.cs_sety(cs, 0, next(i))
        if ndim == 3:
            capi.cs_setz(cs, 0, next(i))

        return capi.create_point(cs)

    def _set_list(self, length, items):
        ptr = self._create_point(length, items)
        if ptr:
            capi.destroy_geom(self.ptr)
            self._ptr = ptr
            self._set_cs()
        else:
            # can this happen?
            raise GEOSException('Geometry resulting from slice deletion was invalid.')

    def _set_single(self, index, value):
        self._cs.setOrdinate(index, 0, value)

    def __iter__(self):
        "Iterate over coordinates of this Point."
        for i in range(len(self)):
            yield self[i]

    def __len__(self):
        "Return the number of dimensions for this Point (either 0, 2 or 3)."
        if self.empty:
            return 0
        if self.hasz:
            return 3
        else:
            return 2

    def _get_single_external(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        elif index == 2:
            return self.z

    _get_single_internal = _get_single_external

    @property
    def x(self):
        "Return the X component of the Point."
        return self._cs.getOrdinate(0, 0)

    @x.setter
    def x(self, value):
        "Set the X component of the Point."
        self._cs.setOrdinate(0, 0, value)

    @property
    def y(self):
        "Return the Y component of the Point."
        return self._cs.getOrdinate(1, 0)

    @y.setter
    def y(self, value):
        "Set the Y component of the Point."
        self._cs.setOrdinate(1, 0, value)

    @property
    def z(self):
        "Return the Z component of the Point."
        return self._cs.getOrdinate(2, 0) if self.hasz else None

    @z.setter
    def z(self, value):
        "Set the Z component of the Point."
        if not self.hasz:
            raise GEOSException('Cannot set Z on 2D Point.')
        self._cs.setOrdinate(2, 0, value)

    # ### Tuple setting and retrieval routines. ###
    @property
    def tuple(self):
        "Return a tuple of the point."
        return self._cs.tuple

    @tuple.setter
    def tuple(self, tup):
        "Set the coordinates of the point with the given tuple."
        self._cs[0] = tup

    # The tuple and coords properties
    coords = tuple
