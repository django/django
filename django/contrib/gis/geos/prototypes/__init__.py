"""
 This module contains all of the GEOS ctypes function prototypes. Each
 prototype handles the interaction between the GEOS library and Python
 via ctypes.
"""

# Coordinate sequence routines.
from django.contrib.gis.geos.prototypes.coordseq import (create_cs, get_cs,
    cs_clone, cs_getordinate, cs_setordinate, cs_getx, cs_gety, cs_getz,
    cs_setx, cs_sety, cs_setz, cs_getsize, cs_getdims)

# Geometry routines.
from django.contrib.gis.geos.prototypes.geom import (from_hex, from_wkb, from_wkt,
    create_point, create_linestring, create_linearring, create_polygon, create_collection,
    destroy_geom, get_extring, get_intring, get_nrings, get_geomn, geom_clone,
    geos_normalize, geos_type, geos_typeid, geos_get_srid, geos_set_srid,
    get_dims, get_num_coords, get_num_geoms,
    to_hex, to_wkb, to_wkt)

# Miscellaneous routines.
from django.contrib.gis.geos.prototypes.misc import *

# Predicates
from django.contrib.gis.geos.prototypes.predicates import (geos_hasz, geos_isempty,
    geos_isring, geos_issimple, geos_isvalid, geos_contains, geos_crosses,
    geos_disjoint, geos_equals, geos_equalsexact, geos_intersects,
    geos_intersects, geos_overlaps, geos_relatepattern, geos_touches, geos_within)

# Topology routines
from django.contrib.gis.geos.prototypes.topology import *
