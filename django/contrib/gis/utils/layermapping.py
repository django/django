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

  model:
   GeoDjango model (not an instance)

  data:
   OGR-supported data source file (e.g. a shapefile) or
    gdal.DataSource instance

  mapping:
   A python dictionary, keys are strings corresponding
   to the GeoDjango model field, and values correspond to
   string field names for the OGR feature, or if the model field
   is a geographic then it should correspond to the OGR
   geometry type, e.g. 'POINT', 'LINESTRING', 'POLYGON'.

Keyword Args:
  layer:
   The index of the layer to use from the Data Source (defaults to 0)

  source_srs:
   Use this to specify the source SRS manually (for example, 
   some shapefiles don't come with a '.prj' file).  An integer SRID,
   a string WKT, and SpatialReference objects are valid parameters.

  encoding:
   Specifies the encoding of the string in the OGR data source.
   For example, 'latin-1', 'utf-8', and 'cp437' are all valid
   encoding parameters.

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
  Saved: Name: 1
  Saved: Name: 2
  Saved: Name: 3

 LayerMapping just transformed the three geometries from the SHP file from their
  source spatial reference system (WGS84) to the spatial reference system of
  the GeoDjango model (NAD83).  If no spatial reference system is defined for
  the layer, use the `source_srs` keyword with a SpatialReference object to
  specify one. Further, data is selectively imported from the given data source 
  fields into the model fields.
"""
from types import StringType, TupleType
from datetime import datetime
from django.contrib.gis.db.backend import SPATIAL_BACKEND
from django.contrib.gis.gdal import \
     OGRGeometry, OGRGeomType, SpatialReference, CoordTransform, \
     DataSource, OGRException
from django.contrib.gis.gdal.field import Field, OFTInteger, OFTReal, OFTString, OFTDateTime
from django.contrib.gis.models import GeometryColumns, SpatialRefSys
from django.db import connection, transaction
from django.core.exceptions import ObjectDoesNotExist

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

def map_foreign_key(django_field):
    from django.db.models.fields.related import ForeignKey

    if not django_field.__class__ is ForeignKey:
        return django_field.__class__.__name__

     
    rf=django_field.rel.get_related_field()

    return rf.get_internal_type()
                
# The acceptable Django field types that map to OGR fields.
field_types = {
               'AutoField' : OFTInteger,
               'IntegerField' : OFTInteger,
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
        if model_field in model_fields:
            model_type = model_fields[model_field]
        elif model_field[:-3] in model_fields: #foreign key
            model_type = model_fields[model_field[:-3]]
        else:
            raise Exception('Given mapping field "%s" not in given Model fields!' % model_field)

        ### Handling if we get a geometry in the Field ###
        if ogr_field in ogc_types:
            # At this time, no more than one geographic field per model =(
            if HAS_GEO:
                raise Exception('More than one geographic field in mapping not allowed (yet).')
            else:
                HAS_GEO = ogr_field

            # Making sure this geometry field type is a valid Django GIS field.
            if not model_type in gis_fields:
                raise Exception('Unknown Django GIS field type "%s"' % model_type)
            
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
                raise Exception('Invalid mapping geometry; model has %s, feature has %s' % (model_type, gtype))

        ## Handling other fields 
        else:
            # Making sure the model field is
            if not model_type in field_types:
                raise Exception('Django field type "%s" has no OGR mapping (yet).' % model_type)

            # Otherwise, we've got an OGR Field.  Making sure that an
            # index exists for the mapping OGR field.
            try:
                fi = feat.index(ogr_field)
            except:
                raise Exception('Given mapping OGR field "%s" not in given OGR layer feature!' % ogr_field)
                    
def check_layer(layer, fields, mapping):
    "Checks the OGR layer by incrementing through and checking each feature."
    # Incrementing through each feature in the layer.
    for feat in layer:
        check_feature(feat, fields, mapping)

def check_srs(layer, source_srs):
    "Checks the compatibility of the given spatial reference object."
    if isinstance(source_srs, SpatialReference):
        sr = source_srs
    elif isinstance(source_srs, SpatialRefSys):
        sr = source_srs.srs
    elif isinstance(source_srs, (int, str)):
        sr = SpatialReference(source_srs)
    else:
        sr = layer.srs
    if not sr:
        raise Exception('No source reference system defined.')
    else:
        return sr

class LayerMapping:
    "A class that maps OGR Layers to Django Models."

    def __init__(self, model, data, mapping, layer=0, source_srs=None, encoding=None):
        "Takes the Django model, the data source, and the mapping (dictionary)"

        # Getting the field names and types from the model
        fields = dict((f.name, map_foreign_key(f)) for f in model._meta.fields)
        # Getting the DataSource and its Layer
        if isinstance(data, basestring):
            self.ds = DataSource(data)
        else:
            self.ds = data
        self.layer = self.ds[layer]

        # Checking the layer -- intitialization of the object will fail if
        #  things don't check out before hand.
        check_layer(self.layer, fields, mapping)
        
        # Since the layer checked out, setting the fields and the mapping.
        self.fields = fields
        self.mapping = mapping
        self.model = model
        self.source_srs = check_srs(self.layer, source_srs)

        # Setting the encoding for OFTString fields, if specified.
        if encoding:
            # Making sure the encoding exists, if not a LookupError
            #  exception will be thrown.
            from codecs import lookup
            lookup(encoding)
            self.encoding = encoding
        else:
            self.encoding = None

    # Either the import will work, or it won't be committed.
    @transaction.commit_on_success
    def save(self, verbose=False):
        "Runs the layer mapping on the given SHP file, and saves to the database."

        # Getting the GeometryColumn object.
        try:
            db_table = self.model._meta.db_table
            if SPATIAL_BACKEND == 'oracle': db_table = db_table.upper()
            gc_kwargs = {GeometryColumns.table_name_col() : db_table}
            geo_col = GeometryColumns.objects.get(**gc_kwargs)
        except:
            raise Exception('Geometry column does not exist. (did you run syncdb?)')
        
        # Getting the coordinate system needed for transformation (with CoordTransform)  
        try:
            # Getting the target spatial reference system
            target_srs = SpatialRefSys.objects.get(srid=geo_col.srid).srs

            # Creating the CoordTransform object
            ct = CoordTransform(self.source_srs, target_srs)
        except Exception, msg:
            raise Exception('Could not translate between the data source and model geometry: %s' % msg)

        for feat in self.layer:
            # The keyword arguments for model construction
            kwargs = {}

            # Incrementing through each model field and the OGR field in the mapping
            all_prepped = True

            for model_field, ogr_field in self.mapping.items():
                is_fk = False
                try:
                    model_type = self.fields[model_field]
                except KeyError: #foreign key
                    model_type = self.fields[model_field[:-3]]
                    is_fk = True

                if ogr_field in ogc_types:
                    ## Getting the OGR geometry from the field
                    geom = feat.geom

                    if make_multi(geom.geom_name, model_type):
                        # Constructing a multi-geometry type to contain the single geometry
                        multi_type = multi_types[geom.geom_name]
                        g = OGRGeometry(multi_type)
                        g.add(geom)
                    else:
                        g = geom

                    # Transforming the geometry with our Coordinate Transformation object.
                    g.transform(ct)

                    # Updating the keyword args with the WKT of the transformed model.
                    val = g.wkt
                else:
                    ## Otherwise, this is an OGR field type
                    fld = feat[ogr_field]

                    if isinstance(fld, OFTString) and self.encoding:
                        # The encoding for OGR data sources may be specified here
                        #  (e.g., 'cp437' for Census Bureau boundary files).
                        val = unicode(fld.value, self.encoding)
                    else:
                        val = fld.value

                if is_fk:
                    rel_obj = None
                    field_name = model_field[:-3]
                    try:
                        #FIXME: refactor to efficiently fetch FKs.
                        #  Requires significant re-work. :-/
                        rel = self.model._meta.get_field(field_name).rel
                        rel_obj = rel.to._default_manager.get(**{('%s__exact' % rel.field_name):val})
                    except ObjectDoesNotExist:
                        all_prepped = False
                    
                    kwargs[model_field[:-3]] = rel_obj
                else:
                    kwargs[model_field] = val

            # Constructing the model using the constructed keyword args
            if all_prepped:
                m = self.model(**kwargs)

                # Saving the model
                try:
                    if all_prepped:
                        m.save()
                        if verbose: print 'Saved: %s' % str(m)                        
                    else:
                        print "Skipping %s due to missing relation." % kwargs
                except SystemExit:
                    raise
                except Exception, e:
                    print "Failed to save %s\n  Continuing" % kwargs
