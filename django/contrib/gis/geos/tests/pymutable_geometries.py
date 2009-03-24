from django.contrib.gis.geos import *
from random import random

SEQ_LENGTH = 10
SEQ_RANGE = (-1 * SEQ_LENGTH, SEQ_LENGTH)
SEQ_BOUNDS = (-1 * SEQ_LENGTH, -1, 0, SEQ_LENGTH - 1)
SEQ_OUT_OF_BOUNDS = (-1 * SEQ_LENGTH -1 , SEQ_LENGTH)

def seqrange(): return xrange(*SEQ_RANGE)

def random_coord(dim    = 2,           # coordinate dimensions
                 rng    = (-50,50),    # coordinate range
                 num_type     = float,
                 round_coords = True):

    if round_coords:
        num = lambda: num_type(round(random() * (rng[1]-rng[0]) + rng[0]))
    else:
        num = lambda: num_type(random() * (rng[1]-rng[0]) + rng[0])

    return tuple( num() for axis in xrange(dim) )

def random_list(length = SEQ_LENGTH, ring = False, **kwargs):
    result  = [ random_coord(**kwargs) for index in xrange(length) ]
    if ring:
        result[-1] = result[0]

    return result

random_list.single = random_coord

def random_coll(count = SEQ_LENGTH, **kwargs):
    return [ tuple(random_list(**kwargs)) for i in xrange(count) ]

random_coll.single = random_list

class PyMutTestGeom:
    "The Test Geometry class container."
    def __init__(self, geom_type, coords_fcn=random_list, subtype=tuple, **kwargs):
        self.geom_type  = geom_type
        self.subtype    = subtype
        self.coords_fcn = coords_fcn
        self.fcn_args   = kwargs
        self.coords = self.coords_fcn(**kwargs)
        self.geom   = self.make_geom()

    def newitem(self, **kwargs):
        a = self.coords_fcn.single(**kwargs)
        return self.subtype(a), tuple(a)

    @property
    def tuple_coords(self):
        return tuple(self.coords)

    def make_geom(self):
        return self.geom_type(map(self.subtype,self.coords))


def slice_geometries(ring=True):
    testgeoms = [
        PyMutTestGeom(LineString),
        PyMutTestGeom(MultiPoint, subtype=Point),
        PyMutTestGeom(MultiLineString, coords_fcn=random_coll, subtype=LineString),
        ]
    if ring:
        testgeoms.append(PyMutTestGeom(LinearRing, ring=True))

    return testgeoms

def getslice_functions():
    def gs_01(x): x[0:4],
    def gs_02(x): x[5:-1],
    def gs_03(x): x[6:2:-1],
    def gs_04(x): x[:],
    def gs_05(x): x[:3],
    def gs_06(x): x[::2],
    def gs_07(x): x[::-4],
    def gs_08(x): x[7:7],
    def gs_09(x): x[20:],

    # don't really care about ringy-ness here
    return mark_ring(vars(), 'gs_')

def delslice_functions():
    def ds_01(x): del x[0:4]
    def ds_02(x): del x[5:-1]
    def ds_03(x): del x[6:2:-1]
    def ds_04(x): del x[:]     # should this be allowed?
    def ds_05(x): del x[:3]
    def ds_06(x): del x[1:9:2]
    def ds_07(x): del x[::-4]
    def ds_08(x): del x[7:7]
    def ds_09(x): del x[-7:-2]

    return mark_ring(vars(), 'ds_')

def setslice_extended_functions(g):
    a = g.coords_fcn(3, rng=(100,150))
    def maptype(x,a):
        if isinstance(x, list): return a
        else: return map(g.subtype, a)

    def sse_00(x): x[:3:1]      = maptype(x, a)
    def sse_01(x): x[0:3:1]     = maptype(x, a)
    def sse_02(x): x[2:5:1]     = maptype(x, a)
    def sse_03(x): x[-3::1]     = maptype(x, a)
    def sse_04(x): x[-4:-1:1]   = maptype(x, a)
    def sse_05(x): x[8:5:-1]    = maptype(x, a)
    def sse_06(x): x[-6:-9:-1]  = maptype(x, a)
    def sse_07(x): x[:8:3]      = maptype(x, a)
    def sse_08(x): x[1::3]      = maptype(x, a)
    def sse_09(x): x[-2::-3]    = maptype(x, a)
    def sse_10(x): x[7:1:-2]    = maptype(x, a)
    def sse_11(x): x[2:8:2]     = maptype(x, a)

    return mark_ring(vars(), 'sse_')

def setslice_simple_functions(g):
    a = g.coords_fcn(3, rng=(100,150))
    def maptype(x,a):
        if isinstance(x, list): return a
        else: return map(g.subtype, a)

    def ss_00(x): x[:0]  = maptype(x, a)
    def ss_01(x): x[:1]  = maptype(x, a)
    def ss_02(x): x[:2]  = maptype(x, a)
    def ss_03(x): x[:3]  = maptype(x, a)
    def ss_04(x): x[-4:] = maptype(x, a)
    def ss_05(x): x[-3:] = maptype(x, a)
    def ss_06(x): x[-2:] = maptype(x, a)
    def ss_07(x): x[-1:] = maptype(x, a)
    def ss_08(x): x[5:]  = maptype(x, a)
    def ss_09(x): x[:]   = maptype(x, a)
    def ss_10(x): x[4:4] = maptype(x, a)
    def ss_11(x): x[4:5] = maptype(x, a)
    def ss_12(x): x[4:7] = maptype(x, a)
    def ss_13(x): x[4:8] = maptype(x, a)
    def ss_14(x): x[10:] = maptype(x, a)
    def ss_15(x): x[20:30]  = maptype(x, a)
    def ss_16(x): x[-13:-8] = maptype(x, a)
    def ss_17(x): x[-13:-9] = maptype(x, a)
    def ss_18(x): x[-13:-10] = maptype(x, a)
    def ss_19(x): x[-13:-11] = maptype(x, a)

    return mark_ring(vars(), 'ss_')

def test_geos_functions():

    return (
        lambda x: x.num_coords,
        lambda x: x.empty,
        lambda x: x.valid,
        lambda x: x.simple,
        lambda x: x.ring,
        lambda x: x.boundary,
        lambda x: x.convex_hull,
        lambda x: x.extend,
        lambda x: x.area,
        lambda x: x.length,
            )

def mark_ring(locals, name_pat, length=SEQ_LENGTH):
    '''
    Accepts an array of functions which perform slice modifications
    and labels each function as to whether or not it preserves ring-ness
    '''
    func_array = [ val for name, val in locals.items()
                    if hasattr(val, '__call__')
                    and name.startswith(name_pat) ]

    for i in xrange(len(func_array)):
        a = range(length)
        a[-1] = a[0]
        func_array[i](a)
        ring = len(a) == 0 or (len(a) > 3 and a[-1] == a[0])
        func_array[i].ring = ring

    return func_array

def getcoords(o):
    if hasattr(o, 'coords'):
        return o.coords
    else:
        return o
