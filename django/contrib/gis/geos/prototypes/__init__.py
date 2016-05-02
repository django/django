"""
 This module contains all of the GEOS ctypes function prototypes. Each
 prototype handles the interaction between the GEOS library and Python
 via ctypes.
"""

from django.contrib.gis.geos.prototypes.coordseq import (  # NOQA
    create_cs, cs_clone, cs_getdims, cs_getordinate, cs_getsize, cs_getx,
    cs_gety, cs_getz, cs_setordinate, cs_setx, cs_sety, cs_setz, get_cs,
)
from django.contrib.gis.geos.prototypes.geom import (  # NOQA
    create_collection, create_empty_polygon, create_linearring,
    create_linestring, create_point, create_polygon, destroy_geom, from_hex,
    from_wkb, from_wkt, geom_clone, geos_get_srid, geos_normalize,
    geos_set_srid, geos_type, geos_typeid, get_dims, get_extring, get_geomn,
    get_intring, get_nrings, get_num_coords, get_num_geoms, to_hex, to_wkb,
    to_wkt,
)
from django.contrib.gis.geos.prototypes.misc import *  # NOQA
from django.contrib.gis.geos.prototypes.predicates import (  # NOQA
    geos_contains, geos_covers, geos_crosses, geos_disjoint, geos_equals,
    geos_equalsexact, geos_hasz, geos_intersects, geos_isclosed, geos_isempty,
    geos_isring, geos_issimple, geos_isvalid, geos_overlaps,
    geos_relatepattern, geos_touches, geos_within,
)
from django.contrib.gis.geos.prototypes.topology import *  # NOQA
