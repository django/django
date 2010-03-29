# LayerMapping -- A Django Model/OGR Layer Mapping Utility
"""
 The LayerMapping class provides a way to map the contents of OGR
 vector files (e.g. SHP files) to Geographic-enabled Django models.

 For more information, please consult the GeoDjango documentation:
   http://geodjango.org/docs/layermapping.html
"""
import sys
from datetime import date, datetime
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections, DEFAULT_DB_ALIAS
from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.gdal import CoordTransform, DataSource, \
    OGRException, OGRGeometry, OGRGeomType, SpatialReference
from django.contrib.gis.gdal.field import \
    OFTDate, OFTDateTime, OFTInteger, OFTReal, OFTString, OFTTime
from django.db import models, transaction
from django.contrib.localflavor.us.models import USStateField

# LayerMapping exceptions.
class LayerMapError(Exception): pass
class InvalidString(LayerMapError): pass
class InvalidDecimal(LayerMapError): pass
class InvalidInteger(LayerMapError): pass
class MissingForeignKey(LayerMapError): pass

class LayerMapping(object):
    "A class that maps OGR Layers to GeoDjango Models."

    # Acceptable 'base' types for a multi-geometry type.
    MULTI_TYPES = {1 : OGRGeomType('MultiPoint'),
                   2 : OGRGeomType('MultiLineString'),
                   3 : OGRGeomType('MultiPolygon'),
                   OGRGeomType('Point25D').num : OGRGeomType('MultiPoint25D'),
                   OGRGeomType('LineString25D').num : OGRGeomType('MultiLineString25D'),
                   OGRGeomType('Polygon25D').num : OGRGeomType('MultiPolygon25D'),
                   }

    # Acceptable Django field types and corresponding acceptable OGR
    # counterparts.
    FIELD_TYPES = {
        models.AutoField : OFTInteger,
        models.IntegerField : (OFTInteger, OFTReal, OFTString),
        models.FloatField : (OFTInteger, OFTReal),
        models.DateField : OFTDate,
        models.DateTimeField : OFTDateTime,
        models.EmailField : OFTString,
        models.TimeField : OFTTime,
        models.DecimalField : (OFTInteger, OFTReal),
        models.CharField : OFTString,
        models.SlugField : OFTString,
        models.TextField : OFTString,
        models.URLField : OFTString,
        USStateField : OFTString,
        models.XMLField : OFTString,
        models.SmallIntegerField : (OFTInteger, OFTReal, OFTString),
        models.PositiveSmallIntegerField : (OFTInteger, OFTReal, OFTString),
        }

    # The acceptable transaction modes.
    TRANSACTION_MODES = {'autocommit' : transaction.autocommit,
                         'commit_on_success' : transaction.commit_on_success,
                         }

    def __init__(self, model, data, mapping, layer=0,
                 source_srs=None, encoding=None,
                 transaction_mode='commit_on_success',
                 transform=True, unique=None, using=DEFAULT_DB_ALIAS):
        """
        A LayerMapping object is initialized using the given Model (not an instance),
        a DataSource (or string path to an OGR-supported data file), and a mapping
        dictionary.  See the module level docstring for more details and keyword
        argument usage.
        """
        # Getting the DataSource and the associated Layer.
        if isinstance(data, basestring):
            self.ds = DataSource(data)
        else:
            self.ds = data
        self.layer = self.ds[layer]

        self.using = using
        self.spatial_backend = connections[using].ops

        # Setting the mapping & model attributes.
        self.mapping = mapping
        self.model = model

        # Checking the layer -- intitialization of the object will fail if
        # things don't check out before hand.
        self.check_layer()

        # Getting the geometry column associated with the model (an
        # exception will be raised if there is no geometry column).
        if self.spatial_backend.mysql:
            transform = False
        else:
            self.geo_field = self.geometry_field()

        # Checking the source spatial reference system, and getting
        # the coordinate transformation object (unless the `transform`
        # keyword is set to False)
        if transform:
            self.source_srs = self.check_srs(source_srs)
            self.transform = self.coord_transform()
        else:
            self.transform = transform

        # Setting the encoding for OFTString fields, if specified.
        if encoding:
            # Making sure the encoding exists, if not a LookupError
            # exception will be thrown.
            from codecs import lookup
            lookup(encoding)
            self.encoding = encoding
        else:
            self.encoding = None

        if unique:
            self.check_unique(unique)
            transaction_mode = 'autocommit' # Has to be set to autocommit.
            self.unique = unique
        else:
            self.unique = None

        # Setting the transaction decorator with the function in the
        # transaction modes dictionary.
        if transaction_mode in self.TRANSACTION_MODES:
            self.transaction_decorator = self.TRANSACTION_MODES[transaction_mode]
            self.transaction_mode = transaction_mode
        else:
            raise LayerMapError('Unrecognized transaction mode: %s' % transaction_mode)

        if using is None:
            pass

    #### Checking routines used during initialization ####
    def check_fid_range(self, fid_range):
        "This checks the `fid_range` keyword."
        if fid_range:
            if isinstance(fid_range, (tuple, list)):
                return slice(*fid_range)
            elif isinstance(fid_range, slice):
                return fid_range
            else:
                raise TypeError
        else:
            return None

    def check_layer(self):
        """
        This checks the Layer metadata, and ensures that it is compatible
        with the mapping information and model.  Unlike previous revisions,
        there is no need to increment through each feature in the Layer.
        """
        # The geometry field of the model is set here.
        # TODO: Support more than one geometry field / model.  However, this
        # depends on the GDAL Driver in use.
        self.geom_field = False
        self.fields = {}

        # Getting lists of the field names and the field types available in
        # the OGR Layer.
        ogr_fields = self.layer.fields
        ogr_field_types = self.layer.field_types

        # Function for determining if the OGR mapping field is in the Layer.
        def check_ogr_fld(ogr_map_fld):
            try:
                idx = ogr_fields.index(ogr_map_fld)
            except ValueError:
                raise LayerMapError('Given mapping OGR field "%s" not found in OGR Layer.' % ogr_map_fld)
            return idx

        # No need to increment through each feature in the model, simply check
        # the Layer metadata against what was given in the mapping dictionary.
        for field_name, ogr_name in self.mapping.items():
            # Ensuring that a corresponding field exists in the model
            # for the given field name in the mapping.
            try:
                model_field = self.model._meta.get_field(field_name)
            except models.fields.FieldDoesNotExist:
                raise LayerMapError('Given mapping field "%s" not in given Model fields.' % field_name)

            # Getting the string name for the Django field class (e.g., 'PointField').
            fld_name = model_field.__class__.__name__

            if isinstance(model_field, GeometryField):
                if self.geom_field:
                    raise LayerMapError('LayerMapping does not support more than one GeometryField per model.')

                # Getting the coordinate dimension of the geometry field.
                coord_dim = model_field.dim

                try:
                    if coord_dim == 3:
                        gtype = OGRGeomType(ogr_name + '25D')
                    else:
                        gtype = OGRGeomType(ogr_name)
                except OGRException:
                    raise LayerMapError('Invalid mapping for GeometryField "%s".' % field_name)

                # Making sure that the OGR Layer's Geometry is compatible.
                ltype = self.layer.geom_type
                if not (ltype.name.startswith(gtype.name) or self.make_multi(ltype, model_field)):
                    raise LayerMapError('Invalid mapping geometry; model has %s%s, '
                                        'layer geometry type is %s.' %
                                        (fld_name, (coord_dim == 3 and '(dim=3)') or '', ltype))

                # Setting the `geom_field` attribute w/the name of the model field
                # that is a Geometry.  Also setting the coordinate dimension
                # attribute.
                self.geom_field = field_name
                self.coord_dim = coord_dim
                fields_val = model_field
            elif isinstance(model_field, models.ForeignKey):
                if isinstance(ogr_name, dict):
                    # Is every given related model mapping field in the Layer?
                    rel_model = model_field.rel.to
                    for rel_name, ogr_field in ogr_name.items():
                        idx = check_ogr_fld(ogr_field)
                        try:
                            rel_field = rel_model._meta.get_field(rel_name)
                        except models.fields.FieldDoesNotExist:
                            raise LayerMapError('ForeignKey mapping field "%s" not in %s fields.' %
                                                (rel_name, rel_model.__class__.__name__))
                    fields_val = rel_model
                else:
                    raise TypeError('ForeignKey mapping must be of dictionary type.')
            else:
                # Is the model field type supported by LayerMapping?
                if not model_field.__class__ in self.FIELD_TYPES:
                    raise LayerMapError('Django field type "%s" has no OGR mapping (yet).' % fld_name)

                # Is the OGR field in the Layer?
                idx = check_ogr_fld(ogr_name)
                ogr_field = ogr_field_types[idx]

                # Can the OGR field type be mapped to the Django field type?
                if not issubclass(ogr_field, self.FIELD_TYPES[model_field.__class__]):
                    raise LayerMapError('OGR field "%s" (of type %s) cannot be mapped to Django %s.' %
                                        (ogr_field, ogr_field.__name__, fld_name))
                fields_val = model_field

            self.fields[field_name] = fields_val

    def check_srs(self, source_srs):
        "Checks the compatibility of the given spatial reference object."

        if isinstance(source_srs, SpatialReference):
            sr = source_srs
        elif isinstance(source_srs, self.spatial_backend.spatial_ref_sys()):
            sr = source_srs.srs
        elif isinstance(source_srs, (int, basestring)):
            sr = SpatialReference(source_srs)
        else:
            # Otherwise just pulling the SpatialReference from the layer
            sr = self.layer.srs

        if not sr:
            raise LayerMapError('No source reference system defined.')
        else:
            return sr

    def check_unique(self, unique):
        "Checks the `unique` keyword parameter -- may be a sequence or string."
        if isinstance(unique, (list, tuple)):
            # List of fields to determine uniqueness with
            for attr in unique:
                if not attr in self.mapping: raise ValueError
        elif isinstance(unique, basestring):
            # Only a single field passed in.
            if unique not in self.mapping: raise ValueError
        else:
            raise TypeError('Unique keyword argument must be set with a tuple, list, or string.')

    #### Keyword argument retrieval routines ####
    def feature_kwargs(self, feat):
        """
        Given an OGR Feature, this will return a dictionary of keyword arguments
        for constructing the mapped model.
        """
        # The keyword arguments for model construction.
        kwargs = {}

        # Incrementing through each model field and OGR field in the
        # dictionary mapping.
        for field_name, ogr_name in self.mapping.items():
            model_field = self.fields[field_name]

            if isinstance(model_field, GeometryField):
                # Verify OGR geometry.
                val = self.verify_geom(feat.geom, model_field)
            elif isinstance(model_field, models.base.ModelBase):
                # The related _model_, not a field was passed in -- indicating
                # another mapping for the related Model.
                val = self.verify_fk(feat, model_field, ogr_name)
            else:
                # Otherwise, verify OGR Field type.
                val = self.verify_ogr_field(feat[ogr_name], model_field)

            # Setting the keyword arguments for the field name with the
            # value obtained above.
            kwargs[field_name] = val

        return kwargs

    def unique_kwargs(self, kwargs):
        """
        Given the feature keyword arguments (from `feature_kwargs`) this routine
        will construct and return the uniqueness keyword arguments -- a subset
        of the feature kwargs.
        """
        if isinstance(self.unique, basestring):
            return {self.unique : kwargs[self.unique]}
        else:
            return dict((fld, kwargs[fld]) for fld in self.unique)

    #### Verification routines used in constructing model keyword arguments. ####
    def verify_ogr_field(self, ogr_field, model_field):
        """
        Verifies if the OGR Field contents are acceptable to the Django
        model field.  If they are, the verified value is returned,
        otherwise the proper exception is raised.
        """
        if (isinstance(ogr_field, OFTString) and
            isinstance(model_field, (models.CharField, models.TextField))):
            if self.encoding:
                # The encoding for OGR data sources may be specified here
                # (e.g., 'cp437' for Census Bureau boundary files).
                val = unicode(ogr_field.value, self.encoding)
            else:
                val = ogr_field.value
                if len(val) > model_field.max_length:
                    raise InvalidString('%s model field maximum string length is %s, given %s characters.' %
                                        (model_field.name, model_field.max_length, len(val)))
        elif isinstance(ogr_field, OFTReal) and isinstance(model_field, models.DecimalField):
            try:
                # Creating an instance of the Decimal value to use.
                d = Decimal(str(ogr_field.value))
            except:
                raise InvalidDecimal('Could not construct decimal from: %s' % ogr_field.value)

            # Getting the decimal value as a tuple.
            dtup = d.as_tuple()
            digits = dtup[1]
            d_idx = dtup[2] # index where the decimal is

            # Maximum amount of precision, or digits to the left of the decimal.
            max_prec = model_field.max_digits - model_field.decimal_places

            # Getting the digits to the left of the decimal place for the
            # given decimal.
            if d_idx < 0:
                n_prec = len(digits[:d_idx])
            else:
                n_prec = len(digits) + d_idx

            # If we have more than the maximum digits allowed, then throw an
            # InvalidDecimal exception.
            if n_prec > max_prec:
                raise InvalidDecimal('A DecimalField with max_digits %d, decimal_places %d must round to an absolute value less than 10^%d.' %
                                     (model_field.max_digits, model_field.decimal_places, max_prec))
            val = d
        elif isinstance(ogr_field, (OFTReal, OFTString)) and isinstance(model_field, models.IntegerField):
            # Attempt to convert any OFTReal and OFTString value to an OFTInteger.
            try:
                val = int(ogr_field.value)
            except:
                raise InvalidInteger('Could not construct integer from: %s' % ogr_field.value)
        else:
            val = ogr_field.value
        return val

    def verify_fk(self, feat, rel_model, rel_mapping):
        """
        Given an OGR Feature, the related model and its dictionary mapping,
        this routine will retrieve the related model for the ForeignKey
        mapping.
        """
        # TODO: It is expensive to retrieve a model for every record --
        #  explore if an efficient mechanism exists for caching related
        #  ForeignKey models.

        # Constructing and verifying the related model keyword arguments.
        fk_kwargs = {}
        for field_name, ogr_name in rel_mapping.items():
            fk_kwargs[field_name] = self.verify_ogr_field(feat[ogr_name], rel_model._meta.get_field(field_name))

        # Attempting to retrieve and return the related model.
        try:
            return rel_model.objects.get(**fk_kwargs)
        except ObjectDoesNotExist:
            raise MissingForeignKey('No ForeignKey %s model found with keyword arguments: %s' % (rel_model.__name__, fk_kwargs))

    def verify_geom(self, geom, model_field):
        """
        Verifies the geometry -- will construct and return a GeometryCollection
        if necessary (for example if the model field is MultiPolygonField while
        the mapped shapefile only contains Polygons).
        """
        # Downgrade a 3D geom to a 2D one, if necessary.
        if self.coord_dim != geom.coord_dim:
            geom.coord_dim = self.coord_dim

        if self.make_multi(geom.geom_type, model_field):
            # Constructing a multi-geometry type to contain the single geometry
            multi_type = self.MULTI_TYPES[geom.geom_type.num]
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

    #### Other model methods ####
    def coord_transform(self):
        "Returns the coordinate transformation object."
        SpatialRefSys = self.spatial_backend.spatial_ref_sys()
        try:
            # Getting the target spatial reference system
            target_srs = SpatialRefSys.objects.get(srid=self.geo_field.srid).srs

            # Creating the CoordTransform object
            return CoordTransform(self.source_srs, target_srs)
        except Exception, msg:
            raise LayerMapError('Could not translate between the data source and model geometry: %s' % msg)

    def geometry_field(self):
        "Returns the GeometryField instance associated with the geographic column."
        # Use the `get_field_by_name` on the model's options so that we
        # get the correct field instance if there's model inheritance.
        opts = self.model._meta
        fld, model, direct, m2m = opts.get_field_by_name(self.geom_field)
        return fld

    def make_multi(self, geom_type, model_field):
        """
        Given the OGRGeomType for a geometry and its associated GeometryField,
        determine whether the geometry should be turned into a GeometryCollection.
        """
        return (geom_type.num in self.MULTI_TYPES and
                model_field.__class__.__name__ == 'Multi%s' % geom_type.django)

    def save(self, verbose=False, fid_range=False, step=False,
             progress=False, silent=False, stream=sys.stdout, strict=False):
        """
        Saves the contents from the OGR DataSource Layer into the database
        according to the mapping dictionary given at initialization.

        Keyword Parameters:
         verbose:
           If set, information will be printed subsequent to each model save
           executed on the database.

         fid_range:
           May be set with a slice or tuple of (begin, end) feature ID's to map
           from the data source.  In other words, this keyword enables the user
           to selectively import a subset range of features in the geographic
           data source.

         step:
           If set with an integer, transactions will occur at every step
           interval. For example, if step=1000, a commit would occur after
           the 1,000th feature, the 2,000th feature etc.

         progress:
           When this keyword is set, status information will be printed giving
           the number of features processed and sucessfully saved.  By default,
           progress information will pe printed every 1000 features processed,
           however, this default may be overridden by setting this keyword with an
           integer for the desired interval.

         stream:
           Status information will be written to this file handle.  Defaults to
           using `sys.stdout`, but any object with a `write` method is supported.

         silent:
           By default, non-fatal error notifications are printed to stdout, but
           this keyword may be set to disable these notifications.

         strict:
           Execution of the model mapping will cease upon the first error
           encountered.  The default behavior is to attempt to continue.
        """
        # Getting the default Feature ID range.
        default_range = self.check_fid_range(fid_range)

        # Setting the progress interval, if requested.
        if progress:
            if progress is True or not isinstance(progress, int):
                progress_interval = 1000
            else:
                progress_interval = progress

        # Defining the 'real' save method, utilizing the transaction
        # decorator created during initialization.
        @self.transaction_decorator
        def _save(feat_range=default_range, num_feat=0, num_saved=0):
            if feat_range:
                layer_iter = self.layer[feat_range]
            else:
                layer_iter = self.layer

            for feat in layer_iter:
                num_feat += 1
                # Getting the keyword arguments
                try:
                    kwargs = self.feature_kwargs(feat)
                except LayerMapError, msg:
                    # Something borked the validation
                    if strict: raise
                    elif not silent:
                        stream.write('Ignoring Feature ID %s because: %s\n' % (feat.fid, msg))
                else:
                    # Constructing the model using the keyword args
                    is_update = False
                    if self.unique:
                        # If we want unique models on a particular field, handle the
                        # geometry appropriately.
                        try:
                            # Getting the keyword arguments and retrieving
                            # the unique model.
                            u_kwargs = self.unique_kwargs(kwargs)
                            m = self.model.objects.using(self.using).get(**u_kwargs)
                            is_update = True

                            # Getting the geometry (in OGR form), creating
                            # one from the kwargs WKT, adding in additional
                            # geometries, and update the attribute with the
                            # just-updated geometry WKT.
                            geom = getattr(m, self.geom_field).ogr
                            new = OGRGeometry(kwargs[self.geom_field])
                            for g in new: geom.add(g)
                            setattr(m, self.geom_field, geom.wkt)
                        except ObjectDoesNotExist:
                            # No unique model exists yet, create.
                            m = self.model(**kwargs)
                    else:
                        m = self.model(**kwargs)

                    try:
                        # Attempting to save.
                        m.save(using=self.using)
                        num_saved += 1
                        if verbose: stream.write('%s: %s\n' % (is_update and 'Updated' or 'Saved', m))
                    except SystemExit:
                        raise
                    except Exception, msg:
                        if self.transaction_mode == 'autocommit':
                            # Rolling back the transaction so that other model saves
                            # will work.
                            transaction.rollback_unless_managed()
                        if strict:
                            # Bailing out if the `strict` keyword is set.
                            if not silent:
                                stream.write('Failed to save the feature (id: %s) into the model with the keyword arguments:\n' % feat.fid)
                                stream.write('%s\n' % kwargs)
                            raise
                        elif not silent:
                            stream.write('Failed to save %s:\n %s\nContinuing\n' % (kwargs, msg))

                # Printing progress information, if requested.
                if progress and num_feat % progress_interval == 0:
                    stream.write('Processed %d features, saved %d ...\n' % (num_feat, num_saved))

            # Only used for status output purposes -- incremental saving uses the
            # values returned here.
            return num_saved, num_feat

        nfeat = self.layer.num_feat
        if step and isinstance(step, int) and step < nfeat:
            # Incremental saving is requested at the given interval (step)
            if default_range:
                raise LayerMapError('The `step` keyword may not be used in conjunction with the `fid_range` keyword.')
            beg, num_feat, num_saved = (0, 0, 0)
            indices = range(step, nfeat, step)
            n_i = len(indices)

            for i, end in enumerate(indices):
                # Constructing the slice to use for this step; the last slice is
                # special (e.g, [100:] instead of [90:100]).
                if i+1 == n_i: step_slice = slice(beg, None)
                else: step_slice = slice(beg, end)

                try:
                    num_feat, num_saved = _save(step_slice, num_feat, num_saved)
                    beg = end
                except:
                    stream.write('%s\nFailed to save slice: %s\n' % ('=-' * 20, step_slice))
                    raise
        else:
            # Otherwise, just calling the previously defined _save() function.
            _save()
