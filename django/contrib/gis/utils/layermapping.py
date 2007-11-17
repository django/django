# LayerMapping -- A Django Model/OGR Layer Mapping Utility
"""
 The LayerMapping class provides a way to map the contents of OGR
 vector files (e.g. SHP files) to Geographic-enabled Django models.

 This grew out of my personal needs, specifically the code repetition
 that went into pulling geometries and fields out of an OGR layer,
 converting to another coordinate system (e.g. WGS84), and then inserting
 into a GeoDjango model.

 This utility is still in early stages of development, so its usage
 is subject to change -- please report any bugs.

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

  check:
   By default, LayerMapping increments through each feature in the
   layer to ensure that it is compatible with the given model and
   mapping.  Setting this keyword to False, disables this action,
   which will speed up execution time for very large files.

  silent:
   By default, non-fatal error notifications are printed to stdout; this
   keyword may be set in order to disable these notifications.

  strict:
   Setting this keyword to True will instruct the save() method to
   cease execution on the first error encountered.

  transaction_mode:
   May be 'commit_on_success' (default) or 'autocommit'.

  transform:
   Setting this to False will disable all coordinate transformations.  

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
 specify one.
"""
from datetime import date, datetime
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction
from django.db.models.fields.related import ForeignKey
from django.contrib.gis.db.backend import SPATIAL_BACKEND
from django.contrib.gis.gdal import CoordTransform, DataSource, \
    OGRException, OGRGeometry, OGRGeomType, SpatialReference
from django.contrib.gis.gdal.field import OFTDate, OFTDateTime, OFTInteger, OFTReal, OFTString, OFTTime
from django.contrib.gis.models import GeometryColumns, SpatialRefSys

# LayerMapping exceptions.
class LayerMapError(Exception): pass
class InvalidString(LayerMapError): pass
class InvalidDecimal(LayerMapError): pass

class LayerMapping(object):
    "A class that maps OGR Layers to GeoDjango Models."
    
    # A mapping of given geometry types to their OGR integer type.
    OGC_TYPES = {'POINT' : OGRGeomType('Point'),
                 'LINESTRING' : OGRGeomType('LineString'),
                 'POLYGON' : OGRGeomType('Polygon'),
                 'MULTIPOINT' : OGRGeomType('MultiPoint'),
                 'MULTILINESTRING' : OGRGeomType('MultiLineString'),
                 'MULTIPOLYGON' : OGRGeomType('MultiPolygon'),
                 'GEOMETRYCOLLECTION' : OGRGeomType('GeometryCollection'),
                 }

    # The django.contrib.gis model types.
    GIS_FIELDS = {'PointField' : 'POINT',
                  'LineStringField': 'LINESTRING',
                  'PolygonField': 'POLYGON',
                  'MultiPointField' : 'MULTIPOINT',
                  'MultiLineStringField' : 'MULTILINESTRING',
                  'MultiPolygonField' : 'MULTIPOLYGON',
                  'GeometryCollectionField' : 'GEOMETRYCOLLECTION',
                  }

    # Acceptable 'base' types for a multi-geometry type.
    MULTI_TYPES = {'POINT' : OGRGeomType('MultiPoint'),
                   'LINESTRING' : OGRGeomType('MultiLineString'),
                   'POLYGON' : OGRGeomType('MultiPolygon'),
                   }

    # The acceptable Django field types that map to OGR fields.
    FIELD_TYPES = {
        'AutoField' : OFTInteger,
        'IntegerField' : OFTInteger,
        'FloatField' : OFTReal,
        'DateField' : OFTDate,
        'DateTimeField' : OFTDateTime,
        'TimeField' : OFTTime,
        'DecimalField' : OFTReal,
        'CharField' : OFTString,
        'TextField' : OFTString,
        'SmallIntegerField' : OFTInteger,
        'PositiveSmallIntegerField' : OFTInteger,
        }

    # The acceptable transaction modes.
    TRANSACTION_MODES = {'autocommit' : transaction.autocommit,
                         'commit_on_success' : transaction.commit_on_success,
                         }

    def __init__(self, model, data, mapping, layer=0, 
                 source_srs=None, encoding=None, check=True, 
                 progress=False, interval=1000, strict=False, silent=False,
                 transaction_mode='commit_on_success', transform=True):
        "Takes the Django model, the data source, and the mapping (dictionary)"

        # Getting the field names and types from the model
        self.fields = dict((f.name, self.map_foreign_key(f)) for f in model._meta.fields)
        self.field_classes = dict((f.name, f) for f in model._meta.fields)

        # Getting the DataSource and its Layer
        if isinstance(data, basestring):
            self.ds = DataSource(data)
        else:
            self.ds = data
        self.layer = self.ds[layer]

        # Setting the mapping
        self.mapping = mapping

        # Setting the model, and getting the geometry column associated 
        # with the model (an exception will be raised if there is no 
        # geometry column).
        self.model = model
        self.geo_col = self.geometry_column()

        # Checking the source spatial reference system, and getting
        # the coordinate transformation object (unless the `transform`
        # keyword is set to False)
        self.source_srs = self.check_srs(source_srs)
        self.transform = transform and self.coord_transform()

        # Checking the layer -- intitialization of the object will fail if
        # things don't check out before hand.  This may be time-consuming,
        # and disabled by setting the `check` keyword to False.
        if check: self.check_layer()

        # The silent, strict, progress, and interval flags.
        self.silent = silent
        self.strict = strict
        self.progress = progress
        self.interval = interval

        # Setting the encoding for OFTString fields, if specified.
        if encoding:
            # Making sure the encoding exists, if not a LookupError
            # exception will be thrown.
            from codecs import lookup
            lookup(encoding)
            self.encoding = encoding
        else:
            self.encoding = None

        # Setting the transaction decorator with the function in the 
        # transaction modes dictionary.
        if transaction_mode in self.TRANSACTION_MODES:
            self.transaction_decorator = self.TRANSACTION_MODES[transaction_mode]
            self.transaction_mode = transaction_mode
        else:
            raise LayerMapError('Unrecognized transaction mode: %s' % transaction_mode)

    def check_feature(self, feat):
        "Checks the OGR feature against the model fields and mapping."
        HAS_GEO = False   

        # Incrementing through each model_field & ogr_field in the given mapping.
        for model_field, ogr_field in self.mapping.items():
            # Making sure the given mapping model field is in the given model fields.
            if model_field in self.fields:
                model_type = self.fields[model_field]
            elif model_field[:-3] in self.fields: #foreign key
                model_type = self.fields[model_field[:-3]]
            else:
                raise LayerMapError('Given mapping field "%s" not in given Model fields!' % model_field)

            ### Handling if we get a geometry in the Field ###
            if ogr_field in self.OGC_TYPES:
                # At this time, no more than one geographic field per model =(
                if HAS_GEO:
                    raise LayerMapError('More than one geographic field in mapping not allowed (yet).')
                else:
                    HAS_GEO = ogr_field

                # Making sure this geometry field type is a valid Django GIS field.
                if not model_type in self.GIS_FIELDS:
                    raise LayerMapError('Unknown Django GIS field type "%s"' % model_type)

                # Getting the OGRGeometry, it's type (an integer) and it's name (a string)
                geom  = feat.geom
                gtype = geom.geom_type
                gname = geom.geom_name

                if self.make_multi(gname, model_type):
                    # Do we have to 'upsample' into a Geometry Collection?
                    pass
                elif gtype == self.OGC_TYPES[self.GIS_FIELDS[model_type]]:
                    # The geometry type otherwise was expected
                    pass
                else:
                    raise LayerMapError('Invalid mapping geometry; model has %s, feature has %s' % (model_type, gtype))
            ### Handling other fields ###
            else:
                # Making sure the model field is supported.
                if not model_type in self.FIELD_TYPES:
                    raise LayerMapError('Django field type "%s" has no OGR mapping (yet).' % model_type)

                # Otherwise, we've got an OGR Field.  Making sure that an
                # index exists for the mapping OGR field.
                try:
                    fi = feat.index(ogr_field)
                except:
                    raise LayerMapError('Given mapping OGR field "%s" not in given OGR layer feature!' % ogr_field)

    def check_layer(self):
        "Checks every feature in this object's layer."
        for feat in self.layer:
            self.check_feature(feat)

    def check_srs(self, source_srs):
        "Checks the compatibility of the given spatial reference object."
        if isinstance(source_srs, SpatialReference):
            sr = source_srs
        elif isinstance(source_srs, SpatialRefSys):
            sr = source_srs.srs
        elif isinstance(source_srs, (int, str)):
            sr = SpatialReference(source_srs)
        else:
            # Otherwise just pulling the SpatialReference from the layer
            sr = self.layer.srs
            
        if not sr:
            raise LayerMapError('No source reference system defined.')
        else:
            return sr

    def coord_transform(self):
        "Returns the coordinate transformation object."
        try:
            # Getting the target spatial reference system
            target_srs = SpatialRefSys.objects.get(srid=self.geo_col.srid).srs
        
            # Creating the CoordTransform object
            return CoordTransform(self.source_srs, target_srs)
        except Exception, msg:
            raise LayerMapError('Could not translate between the data source and model geometry: %s' % msg)

    def feature_kwargs(self, feat):
        "Returns the keyword arguments needed for saving a feature."
        
        # The keyword arguments for model construction.
        kwargs = {}

        # The all_prepped flagged, will be set to False if there's a
        # problem w/a ForeignKey that doesn't exist.
        all_prepped = True

        # Incrementing through each model field and OGR field in the
        # dictionary mapping.
        for model_field, ogr_field in self.mapping.items():
            is_fk = False
            try:
                model_type = self.fields[model_field]
            except KeyError: #foreign key
                # The -3 index is b/c foreign keys are appended w/'_id'.
                model_type = self.fields[model_field[:-3]]
                is_fk = True
            
            if ogr_field in self.OGC_TYPES:
                # Verify OGR geometry.
                val = self.verify_geom(feat.geom, model_type)
            else:
                # Otherwise, verify OGR Field type.
                val = self.verify_field(feat[ogr_field], model_field)

            if is_fk:
                # Handling if foreign key.
                rel_obj = None
                field_name = model_field[:-3]
                try:
                    # FIXME: refactor to efficiently fetch FKs.
                    #  Requires significant re-work. :-/
                    rel = self.model._meta.get_field(field_name).rel
                    rel_obj = rel.to._default_manager.get(**{('%s__exact' % rel.field_name):val})
                except ObjectDoesNotExist:
                    all_prepped = False

                kwargs[model_field[:-3]] = rel_obj
            else:
                kwargs[model_field] = val
            
        return kwargs, all_prepped

    def verify_field(self, fld, model_field):
        """
        Verifies if the OGR Field contents are acceptable to the Django
        model field.  If they are, the verified value is returned, 
        otherwise the proper exception is raised.
        """
        field_class = self.field_classes[model_field]
        if isinstance(fld, OFTString):
            if self.encoding:
                # The encoding for OGR data sources may be specified here
                # (e.g., 'cp437' for Census Bureau boundary files).
                val = unicode(fld.value, self.encoding)
            else:
                val = fld.value
                if len(val) > field_class.max_length:
                    raise InvalidString('%s model field maximum string length is %s, given %s characters.' %
                                        (model_field, field_class.max_length, len(val)))
        elif isinstance(fld, OFTReal):
            try:
                # Creating an instance of the Decimal value to use.
                d = Decimal(str(fld.value))
            except:
                raise InvalidDecimal('Could not construct decimal from: %s' % fld)
            dtup = d.as_tuple()
            if len(dtup[1]) > field_class.max_digits:
                raise InvalidDecimal('More than the maximum # of digits encountered.')
            elif len(dtup[1][dtup[2]:]) > field_class.decimal_places:
                raise InvalidDecimal('More than the maximum # of decimal places encountered.')
            val = d
        else:
            val = fld.value
        return val

    def verify_geom(self, geom, model_type):
        "Verifies the geometry."
        if self.make_multi(geom.geom_name, model_type):
            # Constructing a multi-geometry type to contain the single geometry
            multi_type = self.MULTI_TYPES[geom.geom_name]
            g = OGRGeometry(multi_type)
            g.add(geom)
        else:
            g = geom

        # Transforming the geometry with our Coordinate Transformation object,
        # but only if the class variable `transform` is set w/a CoordTransform 
        # object.
        if self.transform: g.transform(self.transform)
        
        # Returning the WKT of the geometry.
        return g.wkt
        
    def geometry_column(self):
        "Returns the GeometryColumn model associated with the geographic column."
        # Getting the GeometryColumn object.
        try:
            db_table = self.model._meta.db_table
            if SPATIAL_BACKEND == 'oracle': db_table = db_table.upper()
            gc_kwargs = {GeometryColumns.table_name_col() : db_table}
            return GeometryColumns.objects.get(**gc_kwargs)
        except Exception, msg:
            raise LayerMapError('Geometry column does not exist for model. (did you run syncdb?):\n %s' % msg)

    def make_multi(self, geom_name, model_type):
        "Determines whether the geometry should be made into a GeometryCollection."
        return (geom_name in self.MULTI_TYPES) and (model_type.startswith('Multi'))

    def map_foreign_key(self, django_field):
        "Handles fields within foreign keys for the given field."
        if not django_field.__class__ is ForeignKey:
            # Returning the field's class name.
            return django_field.__class__.__name__
        else:
            # Otherwise, getting the type of the related field's
            # from the Foreign key.
            rf = django_field.rel.get_related_field()
            return rf.get_internal_type()

    def save(self, verbose=False):
        "Runs the layer mapping on the given SHP file, and saves to the database."
        
        @self.transaction_decorator
        def _save():
            num_feat = 0
            num_saved = 0

            for feat in self.layer:
                num_feat += 1
                # Getting the keyword arguments
                try:
                    kwargs, all_prepped = self.feature_kwargs(feat)
                except LayerMapError, msg:
                    # Something borked the validation
                    if self.strict: raise
                    elif not self.silent: 
                        print 'Ignoring Feature ID %s because: %s' % (feat.fid, msg)
                else:
                    # Constructing the model using the constructed keyword args
                    if all_prepped:
                        m = self.model(**kwargs)
                        try:
                            m.save()
                            num_saved += 1
                            if verbose: print 'Saved: %s' % m
                        except SystemExit:
                            raise
                        except Exception, msg:
                            if self.transaction_mode == 'autocommit':
                                # Rolling back the transaction so that other model saves
                                # will work.
                                transaction.rollback_unless_managed()
                            if self.strict: 
                                # Bailing out if the `strict` keyword is set.
                                if not self.silent:
                                    print 'Failed to save the feature (id: %s) into the model with the keyword arguments:' % feat.fid
                                    print kwargs
                                raise
                            elif not self.silent:
                                print 'Failed to save %s:\n %s\nContinuing' % (kwargs, msg)
                    else:
                        print 'Skipping %s due to missing relation.' % kwargs

                # Printing progress information, if requested.
                if self.progress and num_feat % self.interval == 0:
                    print 'Processed %d features, saved %d ...' % (num_feat, num_saved)
               
        # Calling our defined function, which will use the specified
        # trasaction mode.
        _save()
