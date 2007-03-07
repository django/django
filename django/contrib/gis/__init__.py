from geos import geomFromWKT, geomToWKT
from decimal import Decimal
from django.db import models
from django.db.models.query import QuerySet


class GeoQuerySet(QuerySet):
    # The list of valid query terms
    # override the local QUERY_TERMS in the namespace 
    # not sure how to do that locals() hackery
    # possibly in the init change its locals() variables
    # not sure if that will work

    QUERY_TERMS = (
    'exact', 'iexact', 'contains', 'icontains', 'overlaps',
    'gt', 'gte', 'lt', 'lte', 'in',
    'startswith', 'istartswith', 'endswith', 'iendswith',
    'range', 'year', 'month', 'day', 'isnull', 'search',
)


def dprint(arg):
    import re
    import inspect
    print re.match("^\s*dprint\(\s*(.+)\s*\)", inspect.stack()[1][4][0]).group(1) + ": " + repr(arg)



class GeometryManager(models.Manager):
    #def filter(self, *args, **kwargs):        
    #    super(Manager, self).filter(*args, **kwargs)
    #    return self.get_query_set().filter(*args, **kwargs)
    
    def get_query_set(self):
        return GeoQuerySet(self.model)




class BoundingBox:

    def _geom(self):
        return geomToWKT(self._g)
        
    geom = property(_geom)

    def _area(self):
        return self._g.area()
    
    area = property(_area)


    def __init__(self, ne, sw):
        """ 
        Create a bounding box using two points 
        This points come from a JSON request, so they are strings
        """
	ne =  [Decimal(i.strip(' ')) for i in  ne[1:-1].split(',')]
        sw =  [Decimal(i.strip(' ')) for i in  sw[1:-1].split(',')]
        ne_lat = ne[0]
        ne_lng = ne[1]
        sw_lat = sw[0]
        sw_lng = sw[1]
        bb =  'POLYGON(('         
        bb +=  str(ne_lng) + " " + str(ne_lat) + "," 
        bb += str(ne_lng) + " " + str(sw_lat) + ","
        bb += str(sw_lng) + " " + str(sw_lat) + ","
        bb += str(sw_lng) + " " + str(ne_lat) + ","
        bb += str(ne_lng) + " " + str(ne_lat) 
        bb += '))'
        self._g = geomFromWKT(bb)
