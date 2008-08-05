"""
 Utilities for manipulating Geometry WKT.
"""

def precision_wkt(geom, prec):
    """
    Returns WKT text of the geometry according to the given precision (an 
    integer or a string).  If the precision is an integer, then the decimal
    places of coordinates WKT will be truncated to that number:

     >>> pnt = Point(5, 23)
     >>> pnt.wkt
     'POINT (5.0000000000000000 23.0000000000000000)'
     >>> precision(geom, 1)
     'POINT (5.0 23.0)'

    If the precision is a string, it must be valid Python format string 
    (e.g., '%20.7f') -- thus, you should know what you're doing.
    """
    if isinstance(prec, int):
        num_fmt = '%%.%df' % prec
    elif isinstance(prec, basestring):
        num_fmt = prec
    else:
        raise TypeError

    # TODO: Support 3D geometries.
    coord_fmt = ' '.join([num_fmt, num_fmt])

    def formatted_coords(coords):
        return ','.join([coord_fmt % c[:2] for c in coords])

    def formatted_poly(poly):
        return ','.join(['(%s)' % formatted_coords(r) for r in poly])

    def formatted_geom(g):
        gtype = str(g.geom_type).upper()
        yield '%s(' % gtype
        if gtype == 'POINT':
            yield formatted_coords((g.coords,))
        elif gtype in ('LINESTRING', 'LINEARRING'):
            yield formatted_coords(g.coords)
        elif gtype in ('POLYGON', 'MULTILINESTRING'):
            yield formatted_poly(g)
        elif gtype == 'MULTIPOINT':
            yield formatted_coords(g.coords)
        elif gtype == 'MULTIPOLYGON':
            yield ','.join(['(%s)' % formatted_poly(p) for p in g])
        elif gtype == 'GEOMETRYCOLLECTION':
            yield ','.join([''.join([wkt for wkt in formatted_geom(child)]) for child in g])
        else:
            raise TypeError
        yield ')'

    return ''.join([wkt for wkt in formatted_geom(geom)])
