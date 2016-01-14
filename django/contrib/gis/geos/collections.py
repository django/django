"""
 This module houses the Geometry Collection objects:
 GeometryCollection, MultiPoint, MultiLineString, and MultiPolygon
"""
import json
import warnings
from ctypes import byref, c_int, c_uint

from django.contrib.gis.geos import prototypes as capi
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.geometry import GEOSGeometry, LinearGeometryMixin
from django.contrib.gis.geos.libgeos import geos_version_info, get_pointer_arr
from django.contrib.gis.geos.linestring import LinearRing, LineString
from django.contrib.gis.geos.point import Point
from django.contrib.gis.geos.polygon import Polygon
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.six.moves import range


class GeometryCollection(GEOSGeometry):
    _typeid = 7

    def __init__(self, *args, **kwargs):
        "Initializes a Geometry Collection from a sequence of Geometry objects."

        # Checking the arguments
        if len(args) == 1:
            # If only one geometry provided or a list of geometries is provided
            #  in the first argument.
            if isinstance(args[0], (tuple, list)):
                init_geoms = args[0]
            else:
                init_geoms = args
        else:
            init_geoms = args

        # Ensuring that only the permitted geometries are allowed in this collection
        # this is moved to list mixin super class
        self._check_allowed(init_geoms)

        # Creating the geometry pointer array.
        collection = self._create_collection(len(init_geoms), iter(init_geoms))
        super(GeometryCollection, self).__init__(collection, **kwargs)

    def __iter__(self):
        "Iterates over each Geometry in the Collection."
        for i in range(len(self)):
            yield self[i]

    def __len__(self):
        "Returns the number of geometries in this Collection."
        return self.num_geom

    # ### Methods for compatibility with ListMixin ###
    def _create_collection(self, length, items):
        # Creating the geometry pointer array.
        geoms = get_pointer_arr(length)
        for i, g in enumerate(items):
            # this is a little sloppy, but makes life easier
            # allow GEOSGeometry types (python wrappers) or pointer types
            geoms[i] = capi.geom_clone(getattr(g, 'ptr', g))

        return capi.create_collection(c_int(self._typeid), byref(geoms), c_uint(length))

    def _get_single_internal(self, index):
        return capi.get_geomn(self.ptr, index)

    def _get_single_external(self, index):
        "Returns the Geometry from this Collection at the given index (0-based)."
        # Checking the index and returning the corresponding GEOS geometry.
        return GEOSGeometry(capi.geom_clone(self._get_single_internal(index)), srid=self.srid)

    def _set_list(self, length, items):
        "Create a new collection, and destroy the contents of the previous pointer."
        prev_ptr = self.ptr
        srid = self.srid
        self.ptr = self._create_collection(length, items)
        if srid:
            self.srid = srid
        capi.destroy_geom(prev_ptr)

    _set_single = GEOSGeometry._set_single_rebuild
    _assign_extended_slice = GEOSGeometry._assign_extended_slice_rebuild

    @property
    def json(self):
        if self.__class__.__name__ == 'GeometryCollection':
            return json.dumps({
                'type': self.__class__.__name__,
                'geometries': [
                    {'type': geom.__class__.__name__, 'coordinates': geom.coords}
                    for geom in self
                ],
            })
        return super(GeometryCollection, self).json
    geojson = json

    @property
    def kml(self):
        "Returns the KML for this Geometry Collection."
        return '<MultiGeometry>%s</MultiGeometry>' % ''.join(g.kml for g in self)

    @property
    def tuple(self):
        "Returns a tuple of all the coordinates in this Geometry Collection"
        return tuple(g.tuple for g in self)
    coords = tuple


# MultiPoint, MultiLineString, and MultiPolygon class definitions.
class MultiPoint(GeometryCollection):
    _allowed = Point
    _typeid = 4


class MultiLineString(LinearGeometryMixin, GeometryCollection):
    _allowed = (LineString, LinearRing)
    _typeid = 5

    @property
    def closed(self):
        if geos_version_info()['version'] < '3.5':
            raise GEOSException("MultiLineString.closed requires GEOS >= 3.5.0.")
        return super(MultiLineString, self).closed


class MultiPolygon(GeometryCollection):
    _allowed = Polygon
    _typeid = 6

    @property
    def cascaded_union(self):
        "Returns a cascaded union of this MultiPolygon."
        warnings.warn(
            "`cascaded_union` is deprecated, use the `unary_union` property instead.",
            RemovedInDjango20Warning, 2
        )
        return GEOSGeometry(capi.geos_cascaded_union(self.ptr), self.srid)

# Setting the allowed types here since GeometryCollection is defined before
# its subclasses.
GeometryCollection._allowed = (Point, LineString, LinearRing, Polygon, MultiPoint, MultiLineString, MultiPolygon)
