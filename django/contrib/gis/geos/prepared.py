from django.contrib.gis.geos.base import GEOSBase
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.prototypes import prepared as capi

class PreparedGeometry(GEOSBase):
    """
    A geometry that is prepared for performing certain operations.
    At the moment this includes the contains covers, and intersects
    operations.
    """
    ptr_type = capi.PREPGEOM_PTR

    def __init__(self, geom):
        if not isinstance(geom, GEOSGeometry): raise TypeError
        self.ptr = capi.geos_prepare(geom.ptr)

    def __del__(self):
        if self._ptr: capi.prepared_destroy(self._ptr)

    def contains(self, other):
        return capi.prepared_contains(self.ptr, other.ptr)

    def contains_properly(self, other):
        return capi.prepared_contains_properly(self.ptr, other.ptr)

    def covers(self, other):
        return capi.prepared_covers(self.ptr, other.ptr)

    def intersects(self, other):
        return capi.prepared_intersects(self.ptr, other.ptr)
