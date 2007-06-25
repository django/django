# LayerMapping -- A Django Model/OGR Layer Mapping Utility
"""
The LayerMapping class provides a way to map the contents of OGR
 vector files (e.g. SHP files) to Geographic-enabled Django models.

This grew out of my personal needs, specifically the code repetition
 that went into pulling geometries and fields out of an OGR layer,
 converting to another coordinate system (e.g. WGS84), and then inserting
 into a Geographic Django model.

This utility is still in early stages of development, so its usage
 is subject to change -- please report any bugs.

TODO: Unit tests and documentation.

Requirements:  OGR C Library (from GDAL) required.

Usage: 
  lm = LayerMapping(model, source_file, mapping) where,

  model -- GeoDjango model (not an instance)

  source_file -- OGR-supported data source file (e.g. a shapefile)

  mapping -- A python dictionary, keys are strings corresponding
             to the GeoDjango model field, and values correspond to
             string field names for the OGR feature, or if the model field
             is a geographic then it should correspond to the OGR
             geometry type, e.g. 'POINT', 'LINESTRING', 'POLYGON'.

 Example:

 1. You need a GDAL-supported data source, like a shapefile.

  Assume we're using the test_poly SHP file:
  >>> from django.contrib.gis.gdal import DataSource
  >>> ds = DataSource('test_poly.shp')
  >>> layer = ds[0]
  >>> print layer.fields # Exploring the fields in the layer, we only want the 'str' field.
  ['float', 'int', 'str']
  >>> print len(layer) # getting the number of features in the layer (should be 3)
  3
  >>> print layer.geom_type # Should be 3 (a Polygon)
  3
  >>> print layer.srs # WGS84
  GEOGCS["GCS_WGS_1984",
      DATUM["WGS_1984",
          SPHEROID["WGS_1984",6378137,298.257223563]],
      PRIMEM["Greenwich",0],
      UNIT["Degree",0.017453292519943295]]

 2. Now we define our corresponding Django model (make sure to use syncdb):

  from django.contrib.gis.db import models
  class TestGeo(models.Model, models.GeoMixin):
      name = models.CharField(maxlength=25) # corresponds to the 'str' field
      poly = models.PolygonField(srid=4269) # we want our model in a different SRID
      objects = models.GeoManager()
      def __str__(self):
          return 'Name: %s' % self.name

 3. Use LayerMapping to extract all the features and place them in the database:

  >>> from django.contrib.gis.utils import LayerMapping
  >>> from geoapp.models import TestGeo
  >>> mapping = {'name' : 'str', # The 'name' model field maps to the 'str' layer field.
                 'poly' : 'POLYGON', # For geometry fields use OGC name.
                 } # The mapping is a dictionary
  >>> lm = LayerMapping(TestGeo, 'test_poly.shp', mapping) 
  >>> lm.save(verbose=True) # Save the layermap, imports the data. 
  >>> lm.save(verbose=True)
  Saved: Name: 1
  Saved: Name: 2
  Saved: Name: 3

 LayerMapping just transformed the three geometries from the SHP file from their
   source spatial reference system (WGS84) to the spatial reference system of
   the GeoDjango model (NAD83).  Further, data is selectively imported from
   the given 
"""
from types import StringType, TupleType
from datetime import datetime
from django.contrib.gis.gdal import \
     OGRGeometry, OGRGeomType, SpatialReference, CoordTransform, \
     DataSource, Layer, Feature, OGRException
from django.contrib.gis.gdal.Field import Field, OFTInteger, OFTReal, OFTString, OFTDateTime
from django.contrib.gis.models import GeometryColumns, SpatialRefSys

# A mapping of given geometry types to their OGR integer type.
ogc_types = {'POINT' : OGRGeomType('Point'),
             'LINESTRING' : OGRGeomType('LineString'),
             'POLYGON' : OGRGeomType('Polygon'),
             'MULTIPOINT' : OGRGeomType('MultiPoint'),
             'MULTILINESTRING' : OGRGeomType('MultiLineString'),
             'MULTIPOLYGON' : OGRGeomType('MultiPolygon'),
             'GEOMETRYCOLLECTION' : OGRGeomType('GeometryCollection'),
             }

# The django.contrib.gis model types.
gis_fields = {'PointField' : 'POINT',
              'LineStringField': 'LINESTRING',
              'PolygonField': 'POLYGON',
              'MultiPointField' : 'MULTIPOINT',
              'MultiLineStringField' : 'MULTILINESTRING',
              'MultiPolygonField' : 'MULTIPOLYGON',
              }

# Acceptable 'base' types for a multi-geometry type.
multi_types = {'POINT' : OGRGeomType('MultiPoint'),
               'LINESTRING' : OGRGeomType('MultiLineString'),
               'POLYGON' : OGRGeomType('MultiPolygon'),
               }
                
# The acceptable Django field types that map to OGR fields.
field_types = {'IntegerField' : OFTInteger,
               'FloatField' : OFTReal,
               'DateTimeField' : OFTDateTime,
               'DecimalField' : OFTReal,
               'CharField' : OFTString,
               'SmallIntegerField' : OFTInteger,
               'PositiveSmallIntegerField' : OFTInteger,
               }

def make_multi(geom_name, model_type):
    "Determines whether the geometry should be made into a GeometryCollection."
    if (geom_name in multi_types) and (model_type.startswith('Multi')):
        return True
    else:
        return False

def check_feature(feat, model_fields, mapping):
    "Checks the OGR layer feature."

    HAS_GEO = False

    # Incrementing through each model_field & ogr_field in the given mapping.
    for model_field, ogr_field in mapping.items():

        # Making sure the given mapping model field is in the given model fields.
        if not model_field in model_fields:
            raise Exception, 'Given mapping field "%s" not in given Model fields!' % model_field
        else:
            model_type = model_fields[model_field]

        ## Handling if we get a geometry in the Field ###
        if ogr_field in ogc_types:
            # At this time, no more than one geographic field per model =(
            if HAS_GEO:
                raise Exception, 'More than one geographic field in mapping not allowed (yet).'
            else:
                HAS_GEO = ogr_field

            # Making sure this geometry field type is a valid Django GIS field.
            if not model_type in gis_fields:
                raise Exception, 'Unknown Django GIS field type "%s"' % model_type
            
            # Getting the OGRGeometry, it's type (an integer) and it's name (a string)
            geom  = feat.geom
            gtype = geom.geom_type
            gname = geom.geom_name
            
            if make_multi(gname, model_type):
                # Do we have to 'upsample' into a Geometry Collection?
                pass
            elif gtype == ogc_types[gis_fields[model_type]]:
                # The geometry type otherwise was expected
                pass
            else:
                raise Exception, 'Invalid mapping geometry!'

        ## Handling other fields 
        else:
            # Making sure the model field is 
            if not model_type in field_types:
                raise Exception, 'Django field type "%s" has no OGR mapping (yet).' % model_type

            # Otherwise, we've got an OGR Field.  Making sure that an
            # index exists for the mapping OGR field.
            try:
                fi = feat.index(ogr_field)
            except:
                raise Exception, 'Given mapping OGR field "%s" not in given OGR layer feature!' % ogr_field
                    
def check_layer(layer, fields, mapping):
    "Checks the OGR layer by incrementing through and checking each feature."
    # Incrementing through each feature in the layer.
    for feat in layer:
        check_feature(feat, fields, mapping)

class LayerMapping:
    "A class that maps OGR Layers to Django Models."

    def __init__(self, model, ogr_file, mapping, layer=0):
        "Takes the Django model, the mapping (dictionary), and the SHP file."

        # Getting the field names and types from the model
        fields = dict((f.name, f.__class__.__name__) for f in model._meta.fields)

        # Getting the DataSource and its Layer
        self.ds = DataSource(ogr_file)
        self.layer = self.ds[layer]

        # Checking the layer -- intitialization of the object will fail if
        #  things don't check out before hand.
        check_layer(self.layer, fields, mapping)
        
        # Since the layer checked out, setting the fields and the mapping.
        self.fields = fields
        self.mapping = mapping
        self.model = model
        
    def save(self, verbose=False):
        "Runs the layer mapping on the given SHP file, and saves to the database."

        # Getting the GeometryColumn object.
        try:
            geo_col = GeometryColumns.objects.get(f_table_name=self.model._meta.db_table)
        except:
            raise Exception, 'Geometry column "%s" does not exist. (did you run syncdb?)'
        
        # Getting the coordinate system needed for transformation (with CoordTransform)  
        try:
            source_srs = self.layer.srs
            target_srs = SpatialRefSys.objects.get(srid=geo_col.srid).srs
            ct = CoordTransform(source_srs, target_srs)
        except:
            raise Exception, 'Could not translate between the data source and model geometry.'
        
        for feat in self.layer:
            # The keyword arguments for model construction
            kwargs = {}

            # Incrementing through each model field and the OGR field in the mapping
            for model_field, ogr_field in self.mapping.items():
                model_type = self.fields[model_field]

                if ogr_field in ogc_types:
                    ## Getting the OGR geometry from the field
                    geom = feat.geom
                    
                    if make_multi(geom.geom_name, model_type):
                        # Constructing a multi-geometry type to contain the single geometry
                        multi_type = multi_types[gname]
                        g = OGRGeometry(multi_type)
                        g.add(geom)
                    else:
                        g = geom

                    # Transforming the geometry with our Coordinate Transformation object.
                    g.transform(ct)

                    # Updating the keyword args with the WKT of the transformed model.
                    kwargs[model_field] = g.wkt
                else:
                    ## Otherwise, this is an OGR field type
                    fi = feat.index(ogr_field)
                    val = feat[fi].value
                    kwargs[model_field] = val

            # Constructing the model using the constructed keyword args
            m = self.model(**kwargs)

            # Saving the model
            m.save()
            if verbose: print 'Saved: %s' % str(m)

