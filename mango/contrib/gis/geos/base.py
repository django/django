from mango.contrib.gis.geos.error import GEOSException
from mango.contrib.gis.ptr import CPointerBase


class GEOSBase(CPointerBase):
    null_ptr_exception_class = GEOSException
