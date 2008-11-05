from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.models.query import sql, QuerySet, Q

from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.db.models.fields import GeometryField, PointField
from django.contrib.gis.db.models.sql import AreaField, DistanceField, GeomField, GeoQuery, GeoWhereNode
from django.contrib.gis.measure import Area, Distance
from django.contrib.gis.models import get_srid_info
qn = connection.ops.quote_name

# For backwards-compatibility; Q object should work just fine
# after queryset-refactor.
class GeoQ(Q): pass

class GeomSQL(object):
    "Simple wrapper object for geometric SQL."
    def __init__(self, geo_sql):
        self.sql = geo_sql
    
    def as_sql(self, *args, **kwargs):
        return self.sql

class GeoQuerySet(QuerySet):
    "The Geographic QuerySet."

    def __init__(self, model=None, query=None):
        super(GeoQuerySet, self).__init__(model=model, query=query)
        self.query = query or GeoQuery(self.model, connection)

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
        elif SpatialBackend.postgis:
            if not geo_field.geodetic:
                # Getting the area units of the geographic field.
                s['select_field'] = AreaField(Area.unit_attname(geo_field._unit_name))
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
        convert_extent = None
        if SpatialBackend.postgis:
            def convert_extent(box, geo_field):
                # TODO: Parsing of BOX3D, Oracle support (patches welcome!)
                # Box text will be something like "BOX(-90.0 30.0, -85.0 40.0)"; 
                # parsing out and returning as a 4-tuple.
                ll, ur = box[4:-1].split(',')
                xmin, ymin = map(float, ll.split())
                xmax, ymax = map(float, ur.split())
                return (xmin, ymin, xmax, ymax)
        elif SpatialBackend.oracle:
            def convert_extent(wkt, geo_field):
                raise NotImplementedError
        return self._spatial_aggregate('extent', convert_func=convert_extent, **kwargs)

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
        kwargs['geo_field_type'] = PointField
        kwargs['agg_field'] = GeometryField
        return self._spatial_aggregate('make_line', **kwargs)

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
        s = {'procedure_fmt' : '%(geo_col)s,%(x)s,%(y)s,%(z)s',
             'procedure_args' : {'x' : x, 'y' : y, 'z' : z},
             'select_field' : GeomField(),
             }
        return self._spatial_attribute('scale', s, **kwargs)

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
        kwargs['agg_field'] = GeometryField
        return self._spatial_aggregate('unionagg', **kwargs)

    ### Private API -- Abstracted DRY routines. ###
    def _spatial_setup(self, att, aggregate=False, desc=None, field_name=None, geo_field_type=None):
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
        procedure_args['geo_col'] = self._geocol_select(geo_field, field_name, aggregate)

        return procedure_args, geo_field

    def _spatial_aggregate(self, att, field_name=None, 
                           agg_field=None, convert_func=None, 
                           geo_field_type=None, tolerance=0.0005):
        """
        DRY routine for calling aggregate spatial stored procedures and
        returning their result to the caller of the function.
        """
        # Constructing the setup keyword arguments.
        setup_kwargs = {'aggregate' : True,
                        'field_name' : field_name,
                        'geo_field_type' : geo_field_type,
                        }
        procedure_args, geo_field = self._spatial_setup(att, **setup_kwargs)
        
        if SpatialBackend.oracle:
            procedure_args['tolerance'] = tolerance
            # Adding in selection SQL for Oracle geometry columns.
            if agg_field is GeometryField: 
                agg_sql = '%s' % SpatialBackend.select
            else: 
                agg_sql = '%s'
            agg_sql =  agg_sql % ('%(function)s(SDOAGGRTYPE(%(geo_col)s,%(tolerance)s))' % procedure_args)
        else:
            agg_sql = '%(function)s(%(geo_col)s)' % procedure_args

        # Wrapping our selection SQL in `GeomSQL` to bypass quoting, and
        # specifying the type of the aggregate field.
        self.query.select = [GeomSQL(agg_sql)]
        self.query.select_fields = [agg_field]

        try:
            # `asql` => not overriding `sql` module.
            asql, params = self.query.as_sql()
        except sql.datastructures.EmptyResultSet:
            return None   

        # Getting a cursor, executing the query, and extracting the returned
        # value from the aggregate function.
        cursor = connection.cursor()
        cursor.execute(asql, params)
        result = cursor.fetchone()[0]
        
        # If the `agg_field` is specified as a GeometryField, then autmatically
        # set up the conversion function.
        if agg_field is GeometryField and not callable(convert_func):
            if SpatialBackend.postgis:
                def convert_geom(hex, geo_field):
                    if hex: return SpatialBackend.Geometry(hex)
                    else: return None
            elif SpatialBackend.oracle:
                def convert_geom(clob, geo_field):
                    if clob: return SpatialBackend.Geometry(clob.read(), geo_field._srid)
                    else: return None
            convert_func = convert_geom

        # Returning the callback function evaluated on the result culled
        # from the executed cursor.
        if callable(convert_func):
            return convert_func(result, geo_field)
        else:
            return result

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
            dist_att = Distance.unit_attname(geo_field._unit_name)

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
        # keyword or wehn calculating the length of geodetic field, make
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
                        # geometry parameter.
                        procedure_fmt += ', %%s'
                    else:
                        # We need to transform the geom to the srid specified in `transform()`,
                        # so wrapping the geometry placeholder in transformation SQL.
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
                        raise TypeError('Spherical distance calculation only supported on PointFields.')
                    if not str(SpatialBackend.Geometry(buffer(params[0].wkb)).geom_type) == 'Point':
                        raise TypeError('Spherical distance calculation only supported with Point Geometry parameters')
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

    def _geocol_select(self, geo_field, field_name, aggregate=False):
        """
        Helper routine for constructing the SQL to select the geographic
        column.  Takes into account if the geographic field is in a
        ForeignKey relation to the current model.
        """
        # If this is an aggregate spatial query, the flag needs to be
        # set on the `GeoQuery` object of this queryset.
        if aggregate: self.query.aggregate = True

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
