from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.models.query import QuerySet, Q, ValuesQuerySet, ValuesListQuerySet

from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.db.models import aggregates
from django.contrib.gis.db.models.fields import GeometryField, PointField
from django.contrib.gis.db.models.sql import AreaField, DistanceField, GeomField, GeoQuery, GeoWhereNode
from django.contrib.gis.measure import Area, Distance
from django.contrib.gis.models import get_srid_info

class GeoQuerySet(QuerySet):
    "The Geographic QuerySet."

    ### Methods overloaded from QuerySet ###
    def __init__(self, model=None, query=None):
        super(GeoQuerySet, self).__init__(model=model, query=query)
        self.query = query or GeoQuery(self.model, connection)

    def values(self, *fields):
        return self._clone(klass=GeoValuesQuerySet, setup=True, _fields=fields)

    def values_list(self, *fields, **kwargs):
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s'
                    % (kwargs.keys(),))
        if flat and len(fields) > 1:
            raise TypeError("'flat' is not valid when values_list is called with more than one field.")
        return self._clone(klass=GeoValuesListQuerySet, setup=True, flat=flat,
                           _fields=fields)

    ### GeoQuerySet Methods ###
    def area(self, tolerance=0.05, **kwargs):
        """
        Returns the area of the geographic field in an `area` attribute on
        each element of this GeoQuerySet.
        """
        # Peforming setup here rather than in `_spatial_attribute` so that
        # we can get the units for `AreaField`.
        procedure_args, geo_field = self._spatial_setup('area', field_name=kwargs.get('field_name', None))
        s = {'procedure_args' : procedure_args,
             'geo_field' : geo_field,
             'setup' : False,
             }
        if SpatialBackend.oracle:
            s['procedure_fmt'] = '%(geo_col)s,%(tolerance)s'
            s['procedure_args']['tolerance'] = tolerance
            s['select_field'] = AreaField('sq_m') # Oracle returns area in units of meters.
        elif SpatialBackend.postgis or SpatialBackend.spatialite:
            if not geo_field.geodetic:
                # Getting the area units of the geographic field.
                s['select_field'] = AreaField(Area.unit_attname(geo_field.units_name))
            else:
                # TODO: Do we want to support raw number areas for geodetic fields?
                raise Exception('Area on geodetic coordinate systems not supported.')
        return self._spatial_attribute('area', s, **kwargs)

    def centroid(self, **kwargs):
        """
        Returns the centroid of the geographic field in a `centroid`
        attribute on each element of this GeoQuerySet.
        """
        return self._geom_attribute('centroid', **kwargs)

    def difference(self, geom, **kwargs):
        """
        Returns the spatial difference of the geographic field in a `difference`
        attribute on each element of this GeoQuerySet.
        """
        return self._geomset_attribute('difference', geom, **kwargs)

    def distance(self, geom, **kwargs):
        """
        Returns the distance from the given geographic field name to the
        given geometry in a `distance` attribute on each element of the
        GeoQuerySet.

        Keyword Arguments:
         `spheroid`  => If the geometry field is geodetic and PostGIS is
                        the spatial database, then the more accurate
                        spheroid calculation will be used instead of the
                        quicker sphere calculation.

         `tolerance` => Used only for Oracle. The tolerance is
                        in meters -- a default of 5 centimeters (0.05)
                        is used.
        """
        return self._distance_attribute('distance', geom, **kwargs)

    def envelope(self, **kwargs):
        """
        Returns a Geometry representing the bounding box of the
        Geometry field in an `envelope` attribute on each element of
        the GeoQuerySet.
        """
        return self._geom_attribute('envelope', **kwargs)

    def extent(self, **kwargs):
        """
        Returns the extent (aggregate) of the features in the GeoQuerySet.  The
        extent will be returned as a 4-tuple, consisting of (xmin, ymin, xmax, ymax).
        """
        return self._spatial_aggregate(aggregates.Extent, **kwargs)

    def geojson(self, precision=8, crs=False, bbox=False, **kwargs):
        """
        Returns a GeoJSON representation of the geomtry field in a `geojson`
        attribute on each element of the GeoQuerySet.

        The `crs` and `bbox` keywords may be set to True if the users wants
        the coordinate reference system and the bounding box to be included
        in the GeoJSON representation of the geometry.
        """
        if not SpatialBackend.postgis or not SpatialBackend.geojson:
            raise NotImplementedError('Only PostGIS 1.3.4+ supports GeoJSON serialization.')
        
        if not isinstance(precision, (int, long)):
            raise TypeError('Precision keyword must be set with an integer.')
        
        # Setting the options flag 
        options = 0
        if crs and bbox: options = 3
        elif crs: options = 1
        elif bbox: options = 2
        s = {'desc' : 'GeoJSON', 
             'procedure_args' : {'precision' : precision, 'options' : options},
             'procedure_fmt' : '%(geo_col)s,%(precision)s,%(options)s',
             }
        return self._spatial_attribute('geojson', s, **kwargs)

    def gml(self, precision=8, version=2, **kwargs):
        """
        Returns GML representation of the given field in a `gml` attribute
        on each element of the GeoQuerySet.
        """
        s = {'desc' : 'GML', 'procedure_args' : {'precision' : precision}}
        if SpatialBackend.postgis:
            # PostGIS AsGML() aggregate function parameter order depends on the
            # version -- uggh.
            major, minor1, minor2 = SpatialBackend.version
            if major >= 1 and (minor1 > 3 or (minor1 == 3 and minor2 > 1)):
                procedure_fmt = '%(version)s,%(geo_col)s,%(precision)s'
            else:
                procedure_fmt = '%(geo_col)s,%(precision)s,%(version)s'
            s['procedure_args'] = {'precision' : precision, 'version' : version}

        return self._spatial_attribute('gml', s, **kwargs)

    def intersection(self, geom, **kwargs):
        """
        Returns the spatial intersection of the Geometry field in
        an `intersection` attribute on each element of this
        GeoQuerySet.
        """
        return self._geomset_attribute('intersection', geom, **kwargs)

    def kml(self, **kwargs):
        """
        Returns KML representation of the geometry field in a `kml`
        attribute on each element of this GeoQuerySet.
        """
        s = {'desc' : 'KML',
             'procedure_fmt' : '%(geo_col)s,%(precision)s',
             'procedure_args' : {'precision' : kwargs.pop('precision', 8)},
             }
        return self._spatial_attribute('kml', s, **kwargs)

    def length(self, **kwargs):
        """
        Returns the length of the geometry field as a `Distance` object
        stored in a `length` attribute on each element of this GeoQuerySet.
        """
        return self._distance_attribute('length', None, **kwargs)

    def make_line(self, **kwargs):
        """
        Creates a linestring from all of the PointField geometries in the
        this GeoQuerySet and returns it.  This is a spatial aggregate
        method, and thus returns a geometry rather than a GeoQuerySet.
        """
        return self._spatial_aggregate(aggregates.MakeLine, geo_field_type=PointField, **kwargs)

    def mem_size(self, **kwargs):
        """
        Returns the memory size (number of bytes) that the geometry field takes
        in a `mem_size` attribute  on each element of this GeoQuerySet.
        """
        return self._spatial_attribute('mem_size', {}, **kwargs)

    def num_geom(self, **kwargs):
        """
        Returns the number of geometries if the field is a
        GeometryCollection or Multi* Field in a `num_geom`
        attribute on each element of this GeoQuerySet; otherwise
        the sets with None.
        """
        return self._spatial_attribute('num_geom', {}, **kwargs)

    def num_points(self, **kwargs):
        """
        Returns the number of points in the first linestring in the
        Geometry field in a `num_points` attribute on each element of
        this GeoQuerySet; otherwise sets with None.
        """
        return self._spatial_attribute('num_points', {}, **kwargs)

    def perimeter(self, **kwargs):
        """
        Returns the perimeter of the geometry field as a `Distance` object
        stored in a `perimeter` attribute on each element of this GeoQuerySet.
        """
        return self._distance_attribute('perimeter', None, **kwargs)

    def point_on_surface(self, **kwargs):
        """
        Returns a Point geometry guaranteed to lie on the surface of the
        Geometry field in a `point_on_surface` attribute on each element
        of this GeoQuerySet; otherwise sets with None.
        """
        return self._geom_attribute('point_on_surface', **kwargs)

    def scale(self, x, y, z=0.0, **kwargs):
        """
        Scales the geometry to a new size by multiplying the ordinates
        with the given x,y,z scale factors.
        """
        if SpatialBackend.spatialite:
            if z != 0.0:
                raise NotImplementedError('SpatiaLite does not support 3D scaling.')
            s = {'procedure_fmt' : '%(geo_col)s,%(x)s,%(y)s',
                 'procedure_args' : {'x' : x, 'y' : y},
                 'select_field' : GeomField(),
                 }
        else:
            s = {'procedure_fmt' : '%(geo_col)s,%(x)s,%(y)s,%(z)s',
                 'procedure_args' : {'x' : x, 'y' : y, 'z' : z},
                 'select_field' : GeomField(),
                 }
        return self._spatial_attribute('scale', s, **kwargs)

    def snap_to_grid(self, *args, **kwargs):
        """
        Snap all points of the input geometry to the grid.  How the
        geometry is snapped to the grid depends on how many arguments
        were given:
          - 1 argument : A single size to snap both the X and Y grids to.
          - 2 arguments: X and Y sizes to snap the grid to.
          - 4 arguments: X, Y sizes and the X, Y origins.
        """
        if False in [isinstance(arg, (float, int, long)) for arg in args]:
            raise TypeError('Size argument(s) for the grid must be a float or integer values.')

        nargs = len(args)
        if nargs == 1:
            size = args[0]
            procedure_fmt = '%(geo_col)s,%(size)s'
            procedure_args = {'size' : size}
        elif nargs == 2:
            xsize, ysize = args
            procedure_fmt = '%(geo_col)s,%(xsize)s,%(ysize)s'
            procedure_args = {'xsize' : xsize, 'ysize' : ysize}
        elif nargs == 4:
            xsize, ysize, xorigin, yorigin = args
            procedure_fmt = '%(geo_col)s,%(xorigin)s,%(yorigin)s,%(xsize)s,%(ysize)s'
            procedure_args = {'xsize' : xsize, 'ysize' : ysize,
                              'xorigin' : xorigin, 'yorigin' : yorigin}
        else:
            raise ValueError('Must provide 1, 2, or 4 arguments to `snap_to_grid`.')

        s = {'procedure_fmt' : procedure_fmt,
             'procedure_args' : procedure_args,
             'select_field' : GeomField(),
             }

        return self._spatial_attribute('snap_to_grid', s, **kwargs)

    def svg(self, **kwargs):
        """
        Returns SVG representation of the geographic field in a `svg`
        attribute on each element of this GeoQuerySet.
        """
        s = {'desc' : 'SVG',
             'procedure_fmt' : '%(geo_col)s,%(rel)s,%(precision)s',
             'procedure_args' : {'rel' : int(kwargs.pop('relative', 0)),
                                 'precision' : kwargs.pop('precision', 8)},
             }
        return self._spatial_attribute('svg', s, **kwargs)

    def sym_difference(self, geom, **kwargs):
        """
        Returns the symmetric difference of the geographic field in a
        `sym_difference` attribute on each element of this GeoQuerySet.
        """
        return self._geomset_attribute('sym_difference', geom, **kwargs)

    def translate(self, x, y, z=0.0, **kwargs):
        """
        Translates the geometry to a new location using the given numeric
        parameters as offsets.
        """
        if SpatialBackend.spatialite:
            if z != 0.0:
                raise NotImplementedError('SpatiaLite does not support 3D translation.')
            s = {'procedure_fmt' : '%(geo_col)s,%(x)s,%(y)s',
                 'procedure_args' : {'x' : x, 'y' : y},
                 'select_field' : GeomField(),
                 }
        else:
            s = {'procedure_fmt' : '%(geo_col)s,%(x)s,%(y)s,%(z)s',
                 'procedure_args' : {'x' : x, 'y' : y, 'z' : z},
                 'select_field' : GeomField(),
                 }
        return self._spatial_attribute('translate', s, **kwargs)

    def transform(self, srid=4326, **kwargs):
        """
        Transforms the given geometry field to the given SRID.  If no SRID is
        provided, the transformation will default to using 4326 (WGS84).
        """
        if not isinstance(srid, (int, long)):
            raise TypeError('An integer SRID must be provided.')
        field_name = kwargs.get('field_name', None)
        tmp, geo_field = self._spatial_setup('transform', field_name=field_name)

        # Getting the selection SQL for the given geographic field.
        field_col = self._geocol_select(geo_field, field_name)

        # Why cascading substitutions? Because spatial backends like
        # Oracle and MySQL already require a function call to convert to text, thus
        # when there's also a transformation we need to cascade the substitutions.
        # For example, 'SDO_UTIL.TO_WKTGEOMETRY(SDO_CS.TRANSFORM( ... )'
        geo_col = self.query.custom_select.get(geo_field, field_col)

        # Setting the key for the field's column with the custom SELECT SQL to
        # override the geometry column returned from the database.
        custom_sel = '%s(%s, %s)' % (SpatialBackend.transform, geo_col, srid)
        # TODO: Should we have this as an alias?
        # custom_sel = '(%s(%s, %s)) AS %s' % (SpatialBackend.transform, geo_col, srid, qn(geo_field.name))
        self.query.transformed_srid = srid # So other GeoQuerySet methods
        self.query.custom_select[geo_field] = custom_sel
        return self._clone()

    def union(self, geom, **kwargs):
        """
        Returns the union of the geographic field with the given
        Geometry in a `union` attribute on each element of this GeoQuerySet.
        """
        return self._geomset_attribute('union', geom, **kwargs)

    def unionagg(self, **kwargs):
        """
        Performs an aggregate union on the given geometry field.  Returns
        None if the GeoQuerySet is empty.  The `tolerance` keyword is for
        Oracle backends only.
        """
        return self._spatial_aggregate(aggregates.Union, **kwargs)

    ### Private API -- Abstracted DRY routines. ###
    def _spatial_setup(self, att, desc=None, field_name=None, geo_field_type=None):
        """
        Performs set up for executing the spatial function.
        """
        # Does the spatial backend support this?
        func = getattr(SpatialBackend, att, False)
        if desc is None: desc = att
        if not func: raise ImproperlyConfigured('%s stored procedure not available.' % desc)

        # Initializing the procedure arguments.
        procedure_args = {'function' : func}

        # Is there a geographic field in the model to perform this
        # operation on?
        geo_field = self.query._geo_field(field_name)
        if not geo_field:
            raise TypeError('%s output only available on GeometryFields.' % func)

        # If the `geo_field_type` keyword was used, then enforce that
        # type limitation.
        if not geo_field_type is None and not isinstance(geo_field, geo_field_type):
            raise TypeError('"%s" stored procedures may only be called on %ss.' % (func, geo_field_type.__name__))

        # Setting the procedure args.
        procedure_args['geo_col'] = self._geocol_select(geo_field, field_name)

        return procedure_args, geo_field

    def _spatial_aggregate(self, aggregate, field_name=None,
                           geo_field_type=None, tolerance=0.05):
        """
        DRY routine for calling aggregate spatial stored procedures and
        returning their result to the caller of the function.
        """
        # Getting the field the geographic aggregate will be called on.
        geo_field = self.query._geo_field(field_name)
        if not geo_field:
            raise TypeError('%s aggregate only available on GeometryFields.' % aggregate.name)

        # Checking if there are any geo field type limitations on this
        # aggregate (e.g. ST_Makeline only operates on PointFields).
        if not geo_field_type is None and not isinstance(geo_field, geo_field_type):
            raise TypeError('%s aggregate may only be called on %ss.' % (aggregate.name, geo_field_type.__name__))

        # Getting the string expression of the field name, as this is the
        # argument taken by `Aggregate` objects.
        agg_col = field_name or geo_field.name

        # Adding any keyword parameters for the Aggregate object. Oracle backends
        # in particular need an additional `tolerance` parameter.
        agg_kwargs = {}
        if SpatialBackend.oracle: agg_kwargs['tolerance'] = tolerance

        # Calling the QuerySet.aggregate, and returning only the value of the aggregate.
        return self.aggregate(geoagg=aggregate(agg_col, **agg_kwargs))['geoagg']

    def _spatial_attribute(self, att, settings, field_name=None, model_att=None):
        """
        DRY routine for calling a spatial stored procedure on a geometry column
        and attaching its output as an attribute of the model.

        Arguments:
         att:
          The name of the spatial attribute that holds the spatial
          SQL function to call.

         settings:
          Dictonary of internal settings to customize for the spatial procedure.

        Public Keyword Arguments:

         field_name:
          The name of the geographic field to call the spatial
          function on.  May also be a lookup to a geometry field
          as part of a foreign key relation.

         model_att:
          The name of the model attribute to attach the output of
          the spatial function to.
        """
        # Default settings.
        settings.setdefault('desc', None)
        settings.setdefault('geom_args', ())
        settings.setdefault('geom_field', None)
        settings.setdefault('procedure_args', {})
        settings.setdefault('procedure_fmt', '%(geo_col)s')
        settings.setdefault('select_params', [])

        # Performing setup for the spatial column, unless told not to.
        if settings.get('setup', True):
            default_args, geo_field = self._spatial_setup(att, desc=settings['desc'], field_name=field_name)
            for k, v in default_args.iteritems(): settings['procedure_args'].setdefault(k, v)
        else:
            geo_field = settings['geo_field']

        # The attribute to attach to the model.
        if not isinstance(model_att, basestring): model_att = att

        # Special handling for any argument that is a geometry.
        for name in settings['geom_args']:
            # Using the field's get_db_prep_lookup() to get any needed
            # transformation SQL -- we pass in a 'dummy' `contains` lookup.
            where, params = geo_field.get_db_prep_lookup('contains', settings['procedure_args'][name])
            # Replacing the procedure format with that of any needed
            # transformation SQL.
            old_fmt = '%%(%s)s' % name
            new_fmt = where[0] % '%%s'
            settings['procedure_fmt'] = settings['procedure_fmt'].replace(old_fmt, new_fmt)
            settings['select_params'].extend(params)

        # Getting the format for the stored procedure.
        fmt = '%%(function)s(%s)' % settings['procedure_fmt']

        # If the result of this function needs to be converted.
        if settings.get('select_field', False):
            sel_fld = settings['select_field']
            if isinstance(sel_fld, GeomField) and SpatialBackend.select:
                self.query.custom_select[model_att] = SpatialBackend.select
            self.query.extra_select_fields[model_att] = sel_fld

        # Finally, setting the extra selection attribute with
        # the format string expanded with the stored procedure
        # arguments.
        return self.extra(select={model_att : fmt % settings['procedure_args']},
                          select_params=settings['select_params'])

    def _distance_attribute(self, func, geom=None, tolerance=0.05, spheroid=False, **kwargs):
        """
        DRY routine for GeoQuerySet distance attribute routines.
        """
        # Setting up the distance procedure arguments.
        procedure_args, geo_field = self._spatial_setup(func, field_name=kwargs.get('field_name', None))

        # If geodetic defaulting distance attribute to meters (Oracle and
        # PostGIS spherical distances return meters).  Otherwise, use the
        # units of the geometry field.
        if geo_field.geodetic:
            dist_att = 'm'
        else:
            dist_att = Distance.unit_attname(geo_field.units_name)

        # Shortcut booleans for what distance function we're using.
        distance = func == 'distance'
        length = func == 'length'
        perimeter = func == 'perimeter'
        if not (distance or length or perimeter):
            raise ValueError('Unknown distance function: %s' % func)

        # The field's get_db_prep_lookup() is used to get any
        # extra distance parameters.  Here we set up the
        # parameters that will be passed in to field's function.
        lookup_params = [geom or 'POINT (0 0)', 0]

        # If the spheroid calculation is desired, either by the `spheroid`
        # keyword or when calculating the length of geodetic field, make
        # sure the 'spheroid' distance setting string is passed in so we
        # get the correct spatial stored procedure.
        if spheroid or (SpatialBackend.postgis and geo_field.geodetic and length):
            lookup_params.append('spheroid')
        where, params = geo_field.get_db_prep_lookup('distance_lte', lookup_params)

        # The `geom_args` flag is set to true if a geometry parameter was
        # passed in.
        geom_args = bool(geom)

        if SpatialBackend.oracle:
            if distance:
                procedure_fmt = '%(geo_col)s,%(geom)s,%(tolerance)s'
            elif length or perimeter:
                procedure_fmt = '%(geo_col)s,%(tolerance)s'
            procedure_args['tolerance'] = tolerance
        else:
            # Getting whether this field is in units of degrees since the field may have
            # been transformed via the `transform` GeoQuerySet method.
            if self.query.transformed_srid:
                u, unit_name, s = get_srid_info(self.query.transformed_srid)
                geodetic = unit_name in geo_field.geodetic_units
            else:
                geodetic = geo_field.geodetic

            if SpatialBackend.spatialite and geodetic:
                raise ValueError('SQLite does not support linear distance calculations on geodetic coordinate systems.')

            if distance:
                if self.query.transformed_srid:
                    # Setting the `geom_args` flag to false because we want to handle
                    # transformation SQL here, rather than the way done by default
                    # (which will transform to the original SRID of the field rather
                    #  than to what was transformed to).
                    geom_args = False
                    procedure_fmt = '%s(%%(geo_col)s, %s)' % (SpatialBackend.transform, self.query.transformed_srid)
                    if geom.srid is None or geom.srid == self.query.transformed_srid:
                        # If the geom parameter srid is None, it is assumed the coordinates
                        # are in the transformed units.  A placeholder is used for the
                        # geometry parameter.  `GeomFromText` constructor is also needed
                        # to wrap geom placeholder for SpatiaLite.
                        if SpatialBackend.spatialite:
                            procedure_fmt += ', %s(%%%%s, %s)' % (SpatialBackend.from_text, self.query.transformed_srid)
                        else:
                            procedure_fmt += ', %%s'
                    else:
                        # We need to transform the geom to the srid specified in `transform()`,
                        # so wrapping the geometry placeholder in transformation SQL.
                        # SpatiaLite also needs geometry placeholder wrapped in `GeomFromText`
                        # constructor.
                        if SpatialBackend.spatialite:
                            procedure_fmt += ', %s(%s(%%%%s, %s), %s)' % (SpatialBackend.transform, SpatialBackend.from_text,
                                                                          geom.srid, self.query.transformed_srid)
                        else:
                            procedure_fmt += ', %s(%%%%s, %s)' % (SpatialBackend.transform, self.query.transformed_srid)
                else:
                    # `transform()` was not used on this GeoQuerySet.
                    procedure_fmt  = '%(geo_col)s,%(geom)s'

                if geodetic:
                    # Spherical distance calculation is needed (because the geographic
                    # field is geodetic). However, the PostGIS ST_distance_sphere/spheroid()
                    # procedures may only do queries from point columns to point geometries
                    # some error checking is required.
                    if not isinstance(geo_field, PointField):
                        raise ValueError('Spherical distance calculation only supported on PointFields.')
                    if not str(SpatialBackend.Geometry(buffer(params[0].wkb)).geom_type) == 'Point':
                        raise ValueError('Spherical distance calculation only supported with Point Geometry parameters')
                    # The `function` procedure argument needs to be set differently for
                    # geodetic distance calculations.
                    if spheroid:
                        # Call to distance_spheroid() requires spheroid param as well.
                        procedure_fmt += ',%(spheroid)s'
                        procedure_args.update({'function' : SpatialBackend.distance_spheroid, 'spheroid' : where[1]})
                    else:
                        procedure_args.update({'function' : SpatialBackend.distance_sphere})
            elif length or perimeter:
                procedure_fmt = '%(geo_col)s'
                if geodetic and length:
                    # There's no `length_sphere`
                    procedure_fmt += ',%(spheroid)s'
                    procedure_args.update({'function' : SpatialBackend.length_spheroid, 'spheroid' : where[1]})

        # Setting up the settings for `_spatial_attribute`.
        s = {'select_field' : DistanceField(dist_att),
             'setup' : False,
             'geo_field' : geo_field,
             'procedure_args' : procedure_args,
             'procedure_fmt' : procedure_fmt,
             }
        if geom_args:
            s['geom_args'] = ('geom',)
            s['procedure_args']['geom'] = geom
        elif geom:
            # The geometry is passed in as a parameter because we handled
            # transformation conditions in this routine.
            s['select_params'] = [SpatialBackend.Adaptor(geom)]
        return self._spatial_attribute(func, s, **kwargs)

    def _geom_attribute(self, func, tolerance=0.05, **kwargs):
        """
        DRY routine for setting up a GeoQuerySet method that attaches a
        Geometry attribute (e.g., `centroid`, `point_on_surface`).
        """
        s = {'select_field' : GeomField(),}
        if SpatialBackend.oracle:
            s['procedure_fmt'] = '%(geo_col)s,%(tolerance)s'
            s['procedure_args'] = {'tolerance' : tolerance}
        return self._spatial_attribute(func, s, **kwargs)

    def _geomset_attribute(self, func, geom, tolerance=0.05, **kwargs):
        """
        DRY routine for setting up a GeoQuerySet method that attaches a
        Geometry attribute and takes a Geoemtry parameter.  This is used
        for geometry set-like operations (e.g., intersection, difference,
        union, sym_difference).
        """
        s = {'geom_args' : ('geom',),
             'select_field' : GeomField(),
             'procedure_fmt' : '%(geo_col)s,%(geom)s',
             'procedure_args' : {'geom' : geom},
            }
        if SpatialBackend.oracle:
            s['procedure_fmt'] += ',%(tolerance)s'
            s['procedure_args']['tolerance'] = tolerance
        return self._spatial_attribute(func, s, **kwargs)

    def _geocol_select(self, geo_field, field_name):
        """
        Helper routine for constructing the SQL to select the geographic
        column.  Takes into account if the geographic field is in a
        ForeignKey relation to the current model.
        """
        opts = self.model._meta
        if not geo_field in opts.fields:
            # Is this operation going to be on a related geographic field?
            # If so, it'll have to be added to the select related information
            # (e.g., if 'location__point' was given as the field name).
            self.query.add_select_related([field_name])
            self.query.pre_sql_setup()
            rel_table, rel_col = self.query.related_select_cols[self.query.related_select_fields.index(geo_field)]
            return self.query._field_column(geo_field, rel_table)
        elif not geo_field in opts.local_fields:
            # This geographic field is inherited from another model, so we have to
            # use the db table for the _parent_ model instead.
            tmp_fld, parent_model, direct, m2m = opts.get_field_by_name(geo_field.name)
            return self.query._field_column(geo_field, parent_model._meta.db_table)
        else:
            return self.query._field_column(geo_field)

class GeoValuesQuerySet(ValuesQuerySet):
    def __init__(self, *args, **kwargs):
        super(GeoValuesQuerySet, self).__init__(*args, **kwargs)
        # This flag tells `resolve_columns` to run the values through
        # `convert_values`.  This ensures that Geometry objects instead
        # of string values are returned with `values()` or `values_list()`.
        self.query.geo_values = True

class GeoValuesListQuerySet(GeoValuesQuerySet, ValuesListQuerySet):
    pass
