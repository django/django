from .base import GEOSBase
from .error import GEOSException
from .libgeos import geos_version_info
from .prototypes import prepared as capi


class PreparedGeometry(GEOSBase):
    """
    A geometry that is prepared for performing certain operations.
    At the moment this includes the contains covers, and intersects
    operations.
    """
    ptr_type = capi.PREPGEOM_PTR

    def __init__(self, geom):
        # Keeping a reference to the original geometry object to prevent it
        # from being garbage collected which could then crash the prepared one
        # See #21662
        self._base_geom = geom
        from .geometry import GEOSGeometry
        if not isinstance(geom, GEOSGeometry):
            raise TypeError
        self.ptr = capi.geos_prepare(geom.ptr)

    def __del__(self):
        if self._ptr and capi:
            capi.prepared_destroy(self._ptr)

    def contains(self, other):
        return capi.prepared_contains(self.ptr, other.ptr)

    def contains_properly(self, other):
        return capi.prepared_contains_properly(self.ptr, other.ptr)

    def covers(self, other):
        return capi.prepared_covers(self.ptr, other.ptr)

    def intersects(self, other):
        return capi.prepared_intersects(self.ptr, other.ptr)

    # Added in GEOS 3.3:

    def crosses(self, other):
        if geos_version_info()['version'] < '3.3.0':
            raise GEOSException("crosses on prepared geometries requires GEOS >= 3.3.0")
        return capi.prepared_crosses(self.ptr, other.ptr)

    def disjoint(self, other):
        if geos_version_info()['version'] < '3.3.0':
            raise GEOSException("disjoint on prepared geometries requires GEOS >= 3.3.0")
        return capi.prepared_disjoint(self.ptr, other.ptr)

    def overlaps(self, other):
        if geos_version_info()['version'] < '3.3.0':
            raise GEOSException("overlaps on prepared geometries requires GEOS >= 3.3.0")
        return capi.prepared_overlaps(self.ptr, other.ptr)

    def touches(self, other):
        if geos_version_info()['version'] < '3.3.0':
            raise GEOSException("touches on prepared geometries requires GEOS >= 3.3.0")
        return capi.prepared_touches(self.ptr, other.ptr)

    def within(self, other):
        if geos_version_info()['version'] < '3.3.0':
            raise GEOSException("within on prepared geometries requires GEOS >= 3.3.0")
        return capi.prepared_within(self.ptr, other.ptr)
