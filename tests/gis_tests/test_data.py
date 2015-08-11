"""
This module has the mock object definitions used to hold reference geometry
for the GEOS and GDAL tests.
"""
import json
import os

from django.utils import six
from django.utils._os import upath
from django.utils.functional import cached_property

# Path where reference test data is located.
TEST_DATA = os.path.join(os.path.dirname(upath(__file__)), 'data')


def tuplize(seq):
    "Turn all nested sequences to tuples in given sequence."
    if isinstance(seq, (list, tuple)):
        return tuple(tuplize(i) for i in seq)
    return seq


def strconvert(d):
    "Converts all keys in dictionary to str type."
    return {str(k): v for k, v in six.iteritems(d)}


def get_ds_file(name, ext):
    return os.path.join(TEST_DATA,
                        name,
                        name + '.%s' % ext
                        )


class TestObj(object):
    """
    Base testing object, turns keyword args into attributes.
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestDS(TestObj):
    """
    Object for testing GDAL data sources.
    """
    def __init__(self, name, **kwargs):
        # Shapefile is default extension, unless specified otherwise.
        ext = kwargs.pop('ext', 'shp')
        self.ds = get_ds_file(name, ext)
        super(TestDS, self).__init__(**kwargs)


class TestGeom(TestObj):
    """
    Testing object used for wrapping reference geometry data
    in GEOS/GDAL tests.
    """
    def __init__(self, **kwargs):
        # Converting lists to tuples of certain keyword args
        # so coordinate test cases will match (JSON has no
        # concept of tuple).
        coords = kwargs.pop('coords', None)
        if coords:
            self.coords = tuplize(coords)

        centroid = kwargs.pop('centroid', None)
        if centroid:
            self.centroid = tuple(centroid)

        ext_ring_cs = kwargs.pop('ext_ring_cs', None)
        if ext_ring_cs:
            ext_ring_cs = tuplize(ext_ring_cs)
        self.ext_ring_cs = ext_ring_cs

        super(TestGeom, self).__init__(**kwargs)


class TestGeomSet(object):
    """
    Each attribute of this object is a list of `TestGeom` instances.
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, [TestGeom(**strconvert(kw)) for kw in value])


class TestDataMixin(object):
    """
    Mixin used for GEOS/GDAL test cases that defines a `geometries`
    property, which returns and/or loads the reference geometry data.
    """
    @cached_property
    def geometries(self):
        # Load up the test geometry data from fixture into global.
        with open(os.path.join(TEST_DATA, 'geometries.json')) as f:
            geometries = json.load(f)
        return TestGeomSet(**strconvert(geometries))
