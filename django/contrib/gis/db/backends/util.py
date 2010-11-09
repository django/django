"""
A collection of utility routines and classes used by the spatial
backends.
"""

def gqn(val):
    """
    The geographic quote name function; used for quoting tables and
    geometries (they use single rather than the double quotes of the
    backend quotename function).
    """
    if isinstance(val, basestring):
        if isinstance(val, unicode): val = val.encode('ascii')
        return "'%s'" % val
    else:
        return str(val)

class SpatialOperation(object):
    """
    Base class for generating spatial SQL.
    """
    sql_template = '%(geo_col)s %(operator)s %(geometry)s'

    def __init__(self, function='', operator='', result='', **kwargs):
        self.function = function
        self.operator = operator
        self.result = result
        self.extra = kwargs

    def as_sql(self, geo_col, geometry='%s'):
        return self.sql_template % self.params(geo_col, geometry)

    def params(self, geo_col, geometry):
        params = {'function' : self.function,
                  'geo_col' : geo_col,
                  'geometry' : geometry,
                  'operator' : self.operator,
                  'result' : self.result,
                  }
        params.update(self.extra)
        return params

class SpatialFunction(SpatialOperation):
    """
    Base class for generating spatial SQL related to a function.
    """
    sql_template = '%(function)s(%(geo_col)s, %(geometry)s)'

    def __init__(self, func, result='', operator='', **kwargs):
        # Getting the function prefix.
        default = {'function' : func,
                   'operator' : operator,
                   'result' : result
                   }
        kwargs.update(default)
        super(SpatialFunction, self).__init__(**kwargs)
