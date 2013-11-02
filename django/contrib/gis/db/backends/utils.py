"""
A collection of utility routines and classes used by the spatial
backends.
"""


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
        return self.sql_template % self.params(geo_col, geometry), []

    def params(self, geo_col, geometry):
        params = {'function': self.function,
                  'geo_col': geo_col,
                  'geometry': geometry,
                  'operator': self.operator,
                  'result': self.result,
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
        default = {'function': func,
                   'operator': operator,
                   'result': result
                   }
        kwargs.update(default)
        super(SpatialFunction, self).__init__(**kwargs)
