# Copyright (c) 2008-2009 Aryeh Leib Taurog, all rights reserved.
# Modified from original contribution by Aryeh Leib Taurog, which was
# released under the New BSD license.

import unittest

from django.contrib.gis.geos import (
    LinearRing,
    LineString,
    MultiPoint,
    Point,
    Polygon,
    fromstr,
)


def api_get_distance(x):
    return x.distance(Point(-200, -200))


def api_get_buffer(x):
    return x.buffer(10)


def api_get_geom_typeid(x):
    return x.geom_typeid


def api_get_num_coords(x):
    return x.num_coords


def api_get_centroid(x):
    return x.centroid


def api_get_empty(x):
    return x.empty


def api_get_valid(x):
    return x.valid


def api_get_simple(x):
    return x.simple


def api_get_ring(x):
    return x.ring


def api_get_boundary(x):
    return x.boundary


def api_get_convex_hull(x):
    return x.convex_hull


def api_get_extent(x):
    return x.extent


def api_get_area(x):
    return x.area


def api_get_length(x):
    return x.length


geos_function_tests = [
    val
    for name, val in vars().items()
    if hasattr(val, "__call__") and name.startswith("api_get_")
]


class GEOSMutationTest(unittest.TestCase):
    """
    Tests Pythonic Mutability of Python GEOS geometry wrappers
    get/set/delitem on a slice, normal list methods
    """

    def test00_GEOSIndexException(self):
        "Testing Geometry IndexError"
        p = Point(1, 2)
        for i in range(-2, 2):
            p._checkindex(i)
        with self.assertRaises(IndexError):
            p._checkindex(2)
        with self.assertRaises(IndexError):
            p._checkindex(-3)

    def test01_PointMutations(self):
        "Testing Point mutations"
        for p in (Point(1, 2, 3), fromstr("POINT (1 2 3)")):
            self.assertEqual(
                p._get_single_external(1), 2.0, "Point _get_single_external"
            )

            # _set_single
            p._set_single(0, 100)
            self.assertEqual(p.coords, (100.0, 2.0, 3.0), "Point _set_single")

            # _set_list
            p._set_list(2, (50, 3141))
            self.assertEqual(p.coords, (50.0, 3141.0), "Point _set_list")

    def test02_PointExceptions(self):
        "Testing Point exceptions"
        with self.assertRaises(TypeError):
            Point(range(1))
        with self.assertRaises(TypeError):
            Point(range(4))

    def test03_PointApi(self):
        "Testing Point API"
        q = Point(4, 5, 3)
        for p in (Point(1, 2, 3), fromstr("POINT (1 2 3)")):
            p[0:2] = [4, 5]
            for f in geos_function_tests:
                self.assertEqual(f(q), f(p), "Point " + f.__name__)

    def test04_LineStringMutations(self):
        "Testing LineString mutations"
        for ls in (
            LineString((1, 0), (4, 1), (6, -1)),
            fromstr("LINESTRING (1 0,4 1,6 -1)"),
        ):
            self.assertEqual(
                ls._get_single_external(1),
                (4.0, 1.0),
                "LineString _get_single_external",
            )

            # _set_single
            ls._set_single(0, (-50, 25))
            self.assertEqual(
                ls.coords,
                ((-50.0, 25.0), (4.0, 1.0), (6.0, -1.0)),
                "LineString _set_single",
            )

            # _set_list
            ls._set_list(2, ((-50.0, 25.0), (6.0, -1.0)))
            self.assertEqual(
                ls.coords, ((-50.0, 25.0), (6.0, -1.0)), "LineString _set_list"
            )

            lsa = LineString(ls.coords)
            for f in geos_function_tests:
                self.assertEqual(f(lsa), f(ls), "LineString " + f.__name__)

    def test05_Polygon(self):
        "Testing Polygon mutations"
        for pg in (
            Polygon(
                ((1, 0), (4, 1), (6, -1), (8, 10), (1, 0)),
                ((5, 4), (6, 4), (6, 3), (5, 4)),
            ),
            fromstr("POLYGON ((1 0,4 1,6 -1,8 10,1 0),(5 4,6 4,6 3,5 4))"),
        ):
            self.assertEqual(
                pg._get_single_external(0),
                LinearRing((1, 0), (4, 1), (6, -1), (8, 10), (1, 0)),
                "Polygon _get_single_external(0)",
            )
            self.assertEqual(
                pg._get_single_external(1),
                LinearRing((5, 4), (6, 4), (6, 3), (5, 4)),
                "Polygon _get_single_external(1)",
            )

            # _set_list
            pg._set_list(
                2,
                (
                    ((1, 2), (10, 0), (12, 9), (-1, 15), (1, 2)),
                    ((4, 2), (5, 2), (5, 3), (4, 2)),
                ),
            )
            self.assertEqual(
                pg.coords,
                (
                    ((1.0, 2.0), (10.0, 0.0), (12.0, 9.0), (-1.0, 15.0), (1.0, 2.0)),
                    ((4.0, 2.0), (5.0, 2.0), (5.0, 3.0), (4.0, 2.0)),
                ),
                "Polygon _set_list",
            )

            lsa = Polygon(*pg.coords)
            for f in geos_function_tests:
                self.assertEqual(f(lsa), f(pg), "Polygon " + f.__name__)

    def test06_Collection(self):
        "Testing Collection mutations"
        points = (
            MultiPoint(*map(Point, ((3, 4), (-1, 2), (5, -4), (2, 8)))),
            fromstr("MULTIPOINT (3 4,-1 2,5 -4,2 8)"),
        )
        for mp in points:
            self.assertEqual(
                mp._get_single_external(2),
                Point(5, -4),
                "Collection _get_single_external",
            )

            mp._set_list(3, map(Point, ((5, 5), (3, -2), (8, 1))))
            self.assertEqual(
                mp.coords, ((5.0, 5.0), (3.0, -2.0), (8.0, 1.0)), "Collection _set_list"
            )

            lsa = MultiPoint(*map(Point, ((5, 5), (3, -2), (8, 1))))
            for f in geos_function_tests:
                self.assertEqual(f(lsa), f(mp), "MultiPoint " + f.__name__)
