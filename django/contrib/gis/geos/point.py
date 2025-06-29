from ctypes import c_uint

from django.contrib.gis import gdal
from django.contrib.gis.geos import prototypes as capi
from django.contrib.gis.geos.coordseq import GEOSCoordSeq
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.geometry import GEOSGeometry


class Point(GEOSGeometry):
    _minlength = 2
    _maxlength = 3
    has_cs = True

    def __init__(self, x=None, y=None, z=None, m=None, srid=None, is_measured=False):
        """
        The Point object may be initialized with either a tuple, or individual
        parameters.

        For example:
        >>> p = Point((5, 23))  # 2D point, tuple input
        >>> p = Point(5, 23, 8)  # 3D Z point, individual parameters
        >>> p = Point((5, 23, 0), is_measured=True)  # 3D M point, tuple input
        >>> p = Point(5, 23, 0, is_measured=True)  # 3D M point, individual parameters
        >>> p = Point(5, 23, 8, 0)  # 4D point, individual parameters
        """
        if x is None:
            coords = []
        elif isinstance(x, (tuple, list)):
            # Here a tuple or list was passed in under the `x` parameter.
            # When a three element tuple or list is provided we do not know if the last
            # is element the Z dimension or M dimension and default to assuming Z.
            coords = x
        elif isinstance(x, (float, int)) and isinstance(y, (float, int)):
            # Here X, Y, and (optionally) Z and M were passed in individually,
            # as parameters.
            if isinstance(z, (float, int)) and isinstance(m, (float, int)):
                coords = [x, y, z, m]
            elif isinstance(z, (float, int)):
                coords = [x, y, z]
            elif isinstance(m, (float, int)):
                coords = [x, y, m]
            else:
                coords = [x, y]
        else:
            raise TypeError("Invalid parameters given for Point initialization.")

        ndim = len(coords)
        if ndim == 4:
            self._z = True
            self._m = True
        elif ndim == 3:
            is_measured = isinstance(m, (float, int)) or is_measured
            self._z = not is_measured
            self._m = is_measured
        else:
            self._z = True
            self._m = True
        cs = GEOSCoordSeq(capi.create_cs(1, ndim), z=self.hasz, m=self.hasm)
        cs[0] = coords
        point = capi.create_point(cs.ptr)
        # Initializing using the address returned from the GEOS
        #  createPoint factory.
        super().__init__(point, srid=srid)

    def _to_pickle_wkb(self):
        return None if self.empty else super()._to_pickle_wkb()

    def _from_pickle_wkb(self, wkb):
        return self._create_empty() if wkb is None else super()._from_pickle_wkb(wkb)

    def _ogr_ptr(self):
        return (
            gdal.geometries.Point._create_empty() if self.empty else super()._ogr_ptr()
        )

    @classmethod
    def _create_empty(cls):
        return cls._create_point(None, None)

    @classmethod
    def _create_point(cls, ndim, coords, is_measured=False):
        """
        Create a coordinate sequence, set X, Y, [Z], [M] and create point
        """
        if not ndim:
            return capi.create_point(None)

        if ndim < 2 or ndim > 4:
            raise TypeError("Invalid point dimension: %s" % ndim)

        cs = capi.create_cs(c_uint(1), c_uint(ndim))
        i = iter(coords)
        capi.cs_setx(cs, 0, next(i))
        capi.cs_sety(cs, 0, next(i))
        if ndim == 3 and is_measured is False:
            capi.cs_setz(cs, 0, next(i))
        if ndim == 3 and is_measured is True:
            capi.cs_setordinate(cs, 0, 3, next(i))
        if ndim == 4:
            capi.cs_setz(cs, 0, next(i))
            capi.cs_setordinate(cs, 0, 3, next(i))
        return capi.create_point(cs)

    def _set_list(self, length, items):
        ptr = self._create_point(length, items)
        if ptr:
            srid = self.srid
            capi.destroy_geom(self.ptr)
            self._ptr = ptr
            if srid is not None:
                self.srid = srid
            self._post_init()
        else:
            # can this happen?
            raise GEOSException("Geometry resulting from slice deletion was invalid.")

    def _set_single(self, index, value):
        self._cs.setOrdinate(index, 0, value)

    def __iter__(self):
        "Iterate over coordinates of this Point."
        for i in range(len(self)):
            yield self[i]

    def __len__(self):
        "Return the number of dimensions for this Point (either 0, 2, 3, or 4)."
        if self.empty:
            return 0
        elif self.hasm:
            return 4
        elif self.hasz:
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
            raise GEOSException("Cannot set Z on 2D Point.")
        self._cs.setOrdinate(2, 0, value)

    @property
    def m(self):
        "Return the M component of the Point."
        return self._cs.getOrdinate(3, 0) if self.hasm else None

    @m.setter
    def m(self, value):
        "Set the M component of the Point."
        if not self.hasm:
            raise GEOSException("Cannot set M on 2D.")
        self._cs.setOrdinate(3, 0, value)

    @property
    def hasz(self):
        "Return whether this coordinate sequence has Z dimension."
        return self._z if hasattr(self, "_z") else super().hasz

    @property
    def hasm(self):
        "Return whether this coordinate sequence has M dimension."
        return self._m if hasattr(self, "_m") else super().hasm

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
