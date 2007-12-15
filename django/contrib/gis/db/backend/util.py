class GeoFieldSQL(object):
    """
    Container for passing values to `parse_lookup` from the various
    backend geometry fields.
    """
    def __init__(self, where=[], params=[]):
        self.where = where
        self.params = params

    def __str__(self):
        return self.as_sql()

    def as_sql(self, quote=False):
        if not quote:
            return self.where[0] % tuple(self.params)
        else:
            # Used for quoting WKT on certain backends.
            tmp_params = ["'%s'" % self.params[0]]
            tmp_params.extend(self.params[1:])
            return self.where[0] % tuple(tmp_params)

class SpatialOperation(object):
    """
    Base class for generating spatial SQL.
    """
    def __init__(self, function='', operator='', result='', beg_subst='', end_subst=''):
        self.function = function
        self.operator = operator
        self.result = result
        self.beg_subst = beg_subst
        try:
            # Try and put the operator and result into to the
            # end substitution.
            self.end_subst = end_subst % (operator, result)
        except TypeError:
            self.end_subst = end_subst

    @property
    def sql_subst(self):
        return ''.join([self.beg_subst, self.end_subst])

    def as_sql(self, geo_col):
        return self.sql_subst % self.params(geo_col)

    def params(self, geo_col):
        return (geo_col, self.operator)

class SpatialFunction(SpatialOperation):
    """
    Base class for generating spatial SQL related to a function.
    """
    def __init__(self, func, beg_subst='%s(%s, %%s', end_subst=')', result='', operator=''):
        # Getting the function prefix.
        kwargs = {'function' : func, 'operator' : operator, 'result' : result,
                  'beg_subst' : beg_subst, 'end_subst' : end_subst,}
        super(SpatialFunction, self).__init__(**kwargs)

    def params(self, geo_col):
        return (self.function, geo_col)
