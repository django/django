"""
 This routine provides shortuct functions to generate ctypes prototypes
 for the GDAL routines.
"""
# OGR Geometry prototypes.
from django.contrib.gis.gdal.prototypes.geom import \
    assign_srs, clone_geom, create_geom, destroy_geom, from_wkb, from_wkt, \
    get_area, get_coord_dims, get_dims, get_envelope, get_geom_count, get_geom_name, get_geom_srs, get_geom_type, get_point_count, get_wkbsize, \
    getx, get_geom_ref, gety, getz, to_gml, to_wkt

# Spatial Reference prototypes.
from django.contrib.gis.gdal.prototypes.srs import \
    clone_srs

# TEMPORARY
from generation import double_output, string_output, void_output
