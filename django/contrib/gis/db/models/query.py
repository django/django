import warnings

from django.contrib.gis.db.models.fields import (
    GeometryField, LineStringField, PointField, get_srid_info,
)
from django.contrib.gis.db.models.lookups import GISLookup
from django.contrib.gis.db.models.sql import (
    AreaField, DistanceField, GeomField, GMLField,
)
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Area, Distance
from django.db import connections
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import RawSQL
from django.db.models.fields import Field
from django.db.models.query import QuerySet
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning


class GeoQuerySet(QuerySet):
    "The Geographic QuerySet."

    # ### GeoQuerySet Methods ###
    def area(self, tolerance=0.05, **kwargs):
        """
        Returns the area of the geographic field in an `area` attribute on
        each element of this GeoQuerySet.
        """
        # Performing setup here rather than in `_spatial_attribute` so that
        # we can get the units for `AreaField`.
        procedure_args, geo_field = self._spatial_setup(
            'area', field_name=kwargs.get('field_name'))
        s = {'procedure_args': procedure_args,
             'geo_field': geo_field,
             'setup': False,
             }
        connection = connections[self.db]
        backend = connection.ops
        if backend.oracle:
            s['procedure_fmt'] = '%(geo_col)s,%(tolerance)s'
            s['procedure_args']['tolerance'] = tolerance
            s['select_field'] = AreaField('sq_m')  # Oracle returns area in units of meters.
        elif backend.postgis or backend.spatialite:
            if backend.geography:
                # Geography fields support area calculation, returns square meters.
                s['select_field'] = AreaField('sq_m')
            elif not geo_field.geodetic(connection):
                # Getting the area units of the geographic field.
                s['select_field'] = AreaField(Area.unit_attname(geo_field.units_name(connection)))
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

    def force_rhr(self, **kwargs):
        """
        Returns a modified version of the Polygon/MultiPolygon in which
        all of the vertices follow the Right-Hand-Rule.  By default,
        this is attached as the `force_rhr` attribute on each element
        of the GeoQuerySet.
        """
        return self._geom_attribute('force_rhr', **kwargs)

    def geojson(self, precision=8, crs=False, bbox=False, **kwargs):
        """
        Returns a GeoJSON representation of the geometry field in a `geojson`
        attribute on each element of the GeoQuerySet.

        The `crs` and `bbox` keywords may be set to True if the user wants
        the coordinate reference system and the bounding box to be included
        in the GeoJSON representation of the geometry.
        """
        backend = connections[self.db].ops
        if not backend.geojson:
            raise NotImplementedError('Only PostGIS and SpatiaLite support GeoJSON serialization.')

        if not isinstance(precision, six.integer_types):
            raise TypeError('Precision keyword must be set with an integer.')

        options = 0
        if crs and bbox:
            options = 3
        elif bbox:
            options = 1
        elif crs:
            options = 2
        s = {'desc': 'GeoJSON',
             'procedure_args': {'precision': precision, 'options': options},
             'procedure_fmt': '%(geo_col)s,%(precision)s,%(options)s',
             }
        return self._spatial_attribute('geojson', s, **kwargs)

    def geohash(self, precision=20, **kwargs):
        """
        Returns a GeoHash representation of the given field in a `geohash`
        attribute on each element of the GeoQuerySet.

        The `precision` keyword may be used to custom the number of
        _characters_ used in the output GeoHash, the default is 20.
        """
        s = {'desc': 'GeoHash',
             'procedure_args': {'precision': precision},
             'procedure_fmt': '%(geo_col)s,%(precision)s',
             }
        return self._spatial_attribute('geohash', s, **kwargs)

    def gml(self, precision=8, version=2, **kwargs):
        """
        Returns GML representation of the given field in a `gml` attribute
        on each element of the GeoQuerySet.
        """
        backend = connections[self.db].ops
        s = {'desc': 'GML', 'procedure_args': {'precision': precision}}
        if backend.postgis:
            s['procedure_fmt'] = '%(version)s,%(geo_col)s,%(precision)s'
            s['procedure_args'] = {'precision': precision, 'version': version}
        if backend.oracle:
            s['select_field'] = GMLField()

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
        s = {'desc': 'KML',
             'procedure_fmt': '%(geo_col)s,%(precision)s',
             'procedure_args': {'precision': kwargs.pop('precision', 8)},
             }
        return self._spatial_attribute('kml', s, **kwargs)

    def length(self, **kwargs):
        """
        Returns the length of the geometry field as a `Distance` object
        stored in a `length` attribute on each element of this GeoQuerySet.
        """
        return self._distance_attribute('length', None, **kwargs)

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

    def reverse_geom(self, **kwargs):
        """
        Reverses the coordinate order of the geometry, and attaches as a
        `reverse` attribute on each element of this GeoQuerySet.
        """
        s = {'select_field': GeomField()}
        kwargs.setdefault('model_att', 'reverse_geom')
        if connections[self.db].ops.oracle:
            s['geo_field_type'] = LineStringField
        return self._spatial_attribute('reverse', s, **kwargs)

    def scale(self, x, y, z=0.0, **kwargs):
        """
        Scales the geometry to a new size by multiplying the ordinates
        with the given x,y,z scale factors.
        """
        if connections[self.db].ops.spatialite:
            if z != 0.0:
                raise NotImplementedError('SpatiaLite does not support 3D scaling.')
            s = {'procedure_fmt': '%(geo_col)s,%(x)s,%(y)s',
                 'procedure_args': {'x': x, 'y': y},
                 'select_field': GeomField(),
                 }
        else:
            s = {'procedure_fmt': '%(geo_col)s,%(x)s,%(y)s,%(z)s',
                 'procedure_args': {'x': x, 'y': y, 'z': z},
                 'select_field': GeomField(),
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
        if False in [isinstance(arg, (float,) + six.integer_types) for arg in args]:
            raise TypeError('Size argument(s) for the grid must be a float or integer values.')

        nargs = len(args)
        if nargs == 1:
            size = args[0]
            procedure_fmt = '%(geo_col)s,%(size)s'
            procedure_args = {'size': size}
        elif nargs == 2:
            xsize, ysize = args
            procedure_fmt = '%(geo_col)s,%(xsize)s,%(ysize)s'
            procedure_args = {'xsize': xsize, 'ysize': ysize}
        elif nargs == 4:
            xsize, ysize, xorigin, yorigin = args
            procedure_fmt = '%(geo_col)s,%(xorigin)s,%(yorigin)s,%(xsize)s,%(ysize)s'
            procedure_args = {'xsize': xsize, 'ysize': ysize,
                              'xorigin': xorigin, 'yorigin': yorigin}
        else:
            raise ValueError('Must provide 1, 2, or 4 arguments to `snap_to_grid`.')

        s = {'procedure_fmt': procedure_fmt,
             'procedure_args': procedure_args,
             'select_field': GeomField(),
             }

        return self._spatial_attribute('snap_to_grid', s, **kwargs)

    def svg(self, relative=False, precision=8, **kwargs):
        """
        Returns SVG representation of the geographic field in a `svg`
        attribute on each element of this GeoQuerySet.

        Keyword Arguments:
         `relative`  => If set to True, this will evaluate the path in
                        terms of relative moves (rather than absolute).

         `precision` => May be used to set the maximum number of decimal
                        digits used in output (defaults to 8).
        """
        relative = int(bool(relative))
        if not isinstance(precision, six.integer_types):
            raise TypeError('SVG precision keyword argument must be an integer.')
        s = {
            'desc': 'SVG',
            'procedure_fmt': '%(geo_col)s,%(rel)s,%(precision)s',
            'procedure_args': {
                'rel': relative,
                'precision': precision,
            }
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
        if connections[self.db].ops.spatialite:
            if z != 0.0:
                raise NotImplementedError('SpatiaLite does not support 3D translation.')
            s = {'procedure_fmt': '%(geo_col)s,%(x)s,%(y)s',
                 'procedure_args': {'x': x, 'y': y},
                 'select_field': GeomField(),
                 }
        else:
            s = {'procedure_fmt': '%(geo_col)s,%(x)s,%(y)s,%(z)s',
                 'procedure_args': {'x': x, 'y': y, 'z': z},
                 'select_field': GeomField(),
                 }
        return self._spatial_attribute('translate', s, **kwargs)

    def transform(self, srid=4326, **kwargs):
        """
        Transforms the given geometry field to the given SRID.  If no SRID is
        provided, the transformation will default to using 4326 (WGS84).
        """
        if not isinstance(srid, six.integer_types):
            raise TypeError('An integer SRID must be provided.')
        field_name = kwargs.get('field_name')
        self._spatial_setup('transform', field_name=field_name)
        self.query.add_context('transformed_srid', srid)
        return self._clone()

    def union(self, geom, **kwargs):
        """
        Returns the union of the geographic field with the given
        Geometry in a `union` attribute on each element of this GeoQuerySet.
        """
        return self._geomset_attribute('union', geom, **kwargs)

    # ### Private API -- Abstracted DRY routines. ###
    def _spatial_setup(self, att, desc=None, field_name=None, geo_field_type=None):
        """
        Performs set up for executing the spatial function.
        """
        # Does the spatial backend support this?
        connection = connections[self.db]
        func = getattr(connection.ops, att, False)
        if desc is None:
            desc = att
        if not func:
            raise NotImplementedError('%s stored procedure not available on '
                                      'the %s backend.' %
                                      (desc, connection.ops.name))

        # Initializing the procedure arguments.
        procedure_args = {'function': func}

        # Is there a geographic field in the model to perform this
        # operation on?
        geo_field = self._geo_field(field_name)
        if not geo_field:
            raise TypeError('%s output only available on GeometryFields.' % func)

        # If the `geo_field_type` keyword was used, then enforce that
        # type limitation.
        if geo_field_type is not None and not isinstance(geo_field, geo_field_type):
            raise TypeError('"%s" stored procedures may only be called on %ss.' % (func, geo_field_type.__name__))

        # Setting the procedure args.
        procedure_args['geo_col'] = self._geocol_select(geo_field, field_name)

        return procedure_args, geo_field

    def _spatial_attribute(self, att, settings, field_name=None, model_att=None):
        """
        DRY routine for calling a spatial stored procedure on a geometry column
        and attaching its output as an attribute of the model.

        Arguments:
         att:
          The name of the spatial attribute that holds the spatial
          SQL function to call.

         settings:
          Dictionary of internal settings to customize for the spatial procedure.

        Public Keyword Arguments:

         field_name:
          The name of the geographic field to call the spatial
          function on.  May also be a lookup to a geometry field
          as part of a foreign key relation.

         model_att:
          The name of the model attribute to attach the output of
          the spatial function to.
        """
        warnings.warn(
            "The %s GeoQuerySet method is deprecated. See GeoDjango Functions "
            "documentation to find the expression-based replacement." % att,
            RemovedInDjango20Warning, stacklevel=2
        )
        # Default settings.
        settings.setdefault('desc', None)
        settings.setdefault('geom_args', ())
        settings.setdefault('geom_field', None)
        settings.setdefault('procedure_args', {})
        settings.setdefault('procedure_fmt', '%(geo_col)s')
        settings.setdefault('select_params', [])

        connection = connections[self.db]

        # Performing setup for the spatial column, unless told not to.
        if settings.get('setup', True):
            default_args, geo_field = self._spatial_setup(
                att, desc=settings['desc'], field_name=field_name,
                geo_field_type=settings.get('geo_field_type'))
            for k, v in six.iteritems(default_args):
                settings['procedure_args'].setdefault(k, v)
        else:
            geo_field = settings['geo_field']

        # The attribute to attach to the model.
        if not isinstance(model_att, six.string_types):
            model_att = att

        # Special handling for any argument that is a geometry.
        for name in settings['geom_args']:
            # Using the field's get_placeholder() routine to get any needed
            # transformation SQL.
            geom = geo_field.get_prep_value(settings['procedure_args'][name])
            params = geo_field._get_db_prep_lookup('contains', geom, connection=connection)
            geom_placeholder = geo_field.get_placeholder(geom, None, connection)

            # Replacing the procedure format with that of any needed
            # transformation SQL.
            old_fmt = '%%(%s)s' % name
            new_fmt = geom_placeholder % '%%s'
            settings['procedure_fmt'] = settings['procedure_fmt'].replace(old_fmt, new_fmt)
            settings['select_params'].extend(params)

        # Getting the format for the stored procedure.
        fmt = '%%(function)s(%s)' % settings['procedure_fmt']

        # If the result of this function needs to be converted.
        if settings.get('select_field'):
            select_field = settings['select_field']
            if connection.ops.oracle:
                select_field.empty_strings_allowed = False
        else:
            select_field = Field()

        # Finally, setting the extra selection attribute with
        # the format string expanded with the stored procedure
        # arguments.
        self.query.add_annotation(
            RawSQL(fmt % settings['procedure_args'], settings['select_params'], select_field),
            model_att)
        return self

    def _distance_attribute(self, func, geom=None, tolerance=0.05, spheroid=False, **kwargs):
        """
        DRY routine for GeoQuerySet distance attribute routines.
        """
        # Setting up the distance procedure arguments.
        procedure_args, geo_field = self._spatial_setup(func, field_name=kwargs.get('field_name'))

        # If geodetic defaulting distance attribute to meters (Oracle and
        # PostGIS spherical distances return meters).  Otherwise, use the
        # units of the geometry field.
        connection = connections[self.db]
        geodetic = geo_field.geodetic(connection)
        geography = geo_field.geography

        if geodetic:
            dist_att = 'm'
        else:
            dist_att = Distance.unit_attname(geo_field.units_name(connection))

        # Shortcut booleans for what distance function we're using and
        # whether the geometry field is 3D.
        distance = func == 'distance'
        length = func == 'length'
        perimeter = func == 'perimeter'
        if not (distance or length or perimeter):
            raise ValueError('Unknown distance function: %s' % func)
        geom_3d = geo_field.dim == 3

        # The field's _get_db_prep_lookup() is used to get any
        # extra distance parameters.  Here we set up the
        # parameters that will be passed in to field's function.
        lookup_params = [geom or 'POINT (0 0)', 0]

        # Getting the spatial backend operations.
        backend = connection.ops

        # If the spheroid calculation is desired, either by the `spheroid`
        # keyword or when calculating the length of geodetic field, make
        # sure the 'spheroid' distance setting string is passed in so we
        # get the correct spatial stored procedure.
        if spheroid or (backend.postgis and geodetic and
                        (not geography) and length):
            lookup_params.append('spheroid')
        lookup_params = geo_field.get_prep_value(lookup_params)
        params = geo_field._get_db_prep_lookup('distance_lte', lookup_params, connection=connection)

        # The `geom_args` flag is set to true if a geometry parameter was
        # passed in.
        geom_args = bool(geom)

        if backend.oracle:
            if distance:
                procedure_fmt = '%(geo_col)s,%(geom)s,%(tolerance)s'
            elif length or perimeter:
                procedure_fmt = '%(geo_col)s,%(tolerance)s'
            procedure_args['tolerance'] = tolerance
        else:
            # Getting whether this field is in units of degrees since the field may have
            # been transformed via the `transform` GeoQuerySet method.
            srid = self.query.get_context('transformed_srid')
            if srid:
                u, unit_name, s = get_srid_info(srid, connection)
                geodetic = unit_name.lower() in geo_field.geodetic_units

            if geodetic and (not connection.features.supports_distance_geodetic or connection.ops.spatialite):
                raise ValueError(
                    'This database does not support linear distance '
                    'calculations on geodetic coordinate systems.'
                )

            if distance:
                if srid:
                    # Setting the `geom_args` flag to false because we want to handle
                    # transformation SQL here, rather than the way done by default
                    # (which will transform to the original SRID of the field rather
                    #  than to what was transformed to).
                    geom_args = False
                    procedure_fmt = '%s(%%(geo_col)s, %s)' % (backend.transform, srid)
                    if geom.srid is None or geom.srid == srid:
                        # If the geom parameter srid is None, it is assumed the coordinates
                        # are in the transformed units.  A placeholder is used for the
                        # geometry parameter.  `GeomFromText` constructor is also needed
                        # to wrap geom placeholder for SpatiaLite.
                        if backend.spatialite:
                            procedure_fmt += ', %s(%%%%s, %s)' % (backend.from_text, srid)
                        else:
                            procedure_fmt += ', %%s'
                    else:
                        # We need to transform the geom to the srid specified in `transform()`,
                        # so wrapping the geometry placeholder in transformation SQL.
                        # SpatiaLite also needs geometry placeholder wrapped in `GeomFromText`
                        # constructor.
                        if backend.spatialite:
                            procedure_fmt += (', %s(%s(%%%%s, %s), %s)' % (
                                backend.transform, backend.from_text,
                                geom.srid, srid))
                        else:
                            procedure_fmt += ', %s(%%%%s, %s)' % (backend.transform, srid)
                else:
                    # `transform()` was not used on this GeoQuerySet.
                    procedure_fmt = '%(geo_col)s,%(geom)s'

                if not geography and geodetic:
                    # Spherical distance calculation is needed (because the geographic
                    # field is geodetic). However, the PostGIS ST_distance_sphere/spheroid()
                    # procedures may only do queries from point columns to point geometries
                    # some error checking is required.
                    if not backend.geography:
                        if not isinstance(geo_field, PointField):
                            raise ValueError('Spherical distance calculation only supported on PointFields.')
                        if not str(Geometry(six.memoryview(params[0].ewkb)).geom_type) == 'Point':
                            raise ValueError(
                                'Spherical distance calculation only supported with '
                                'Point Geometry parameters'
                            )
                    # The `function` procedure argument needs to be set differently for
                    # geodetic distance calculations.
                    if spheroid:
                        # Call to distance_spheroid() requires spheroid param as well.
                        procedure_fmt += ",'%(spheroid)s'"
                        procedure_args.update({'function': backend.distance_spheroid, 'spheroid': params[1]})
                    else:
                        procedure_args.update({'function': backend.distance_sphere})
            elif length or perimeter:
                procedure_fmt = '%(geo_col)s'
                if not geography and geodetic and length:
                    # There's no `length_sphere`, and `length_spheroid` also
                    # works on 3D geometries.
                    procedure_fmt += ",'%(spheroid)s'"
                    procedure_args.update({'function': backend.length_spheroid, 'spheroid': params[1]})
                elif geom_3d and connection.features.supports_3d_functions:
                    # Use 3D variants of perimeter and length routines on supported backends.
                    if perimeter:
                        procedure_args.update({'function': backend.perimeter3d})
                    elif length:
                        procedure_args.update({'function': backend.length3d})

        # Setting up the settings for `_spatial_attribute`.
        s = {'select_field': DistanceField(dist_att),
             'setup': False,
             'geo_field': geo_field,
             'procedure_args': procedure_args,
             'procedure_fmt': procedure_fmt,
             }
        if geom_args:
            s['geom_args'] = ('geom',)
            s['procedure_args']['geom'] = geom
        elif geom:
            # The geometry is passed in as a parameter because we handled
            # transformation conditions in this routine.
            s['select_params'] = [backend.Adapter(geom)]
        return self._spatial_attribute(func, s, **kwargs)

    def _geom_attribute(self, func, tolerance=0.05, **kwargs):
        """
        DRY routine for setting up a GeoQuerySet method that attaches a
        Geometry attribute (e.g., `centroid`, `point_on_surface`).
        """
        s = {'select_field': GeomField()}
        if connections[self.db].ops.oracle:
            s['procedure_fmt'] = '%(geo_col)s,%(tolerance)s'
            s['procedure_args'] = {'tolerance': tolerance}
        return self._spatial_attribute(func, s, **kwargs)

    def _geomset_attribute(self, func, geom, tolerance=0.05, **kwargs):
        """
        DRY routine for setting up a GeoQuerySet method that attaches a
        Geometry attribute and takes a Geoemtry parameter.  This is used
        for geometry set-like operations (e.g., intersection, difference,
        union, sym_difference).
        """
        s = {
            'geom_args': ('geom',),
            'select_field': GeomField(),
            'procedure_fmt': '%(geo_col)s,%(geom)s',
            'procedure_args': {'geom': geom},
        }
        if connections[self.db].ops.oracle:
            s['procedure_fmt'] += ',%(tolerance)s'
            s['procedure_args']['tolerance'] = tolerance
        return self._spatial_attribute(func, s, **kwargs)

    def _geocol_select(self, geo_field, field_name):
        """
        Helper routine for constructing the SQL to select the geographic
        column.  Takes into account if the geographic field is in a
        ForeignKey relation to the current model.
        """
        compiler = self.query.get_compiler(self.db)
        opts = self.model._meta
        if geo_field not in opts.fields:
            # Is this operation going to be on a related geographic field?
            # If so, it'll have to be added to the select related information
            # (e.g., if 'location__point' was given as the field name, then
            # chop the non-relational field and add select_related('location')).
            # Note: the operation really is defined as "must add select related!"
            self.query.add_select_related([field_name.rsplit(LOOKUP_SEP, 1)[0]])
            # Call pre_sql_setup() so that compiler.select gets populated.
            compiler.pre_sql_setup()
            for col, _, _ in compiler.select:
                if col.output_field == geo_field:
                    return col.as_sql(compiler, compiler.connection)[0]
            raise ValueError("%r not in compiler's related_select_cols" % geo_field)
        elif geo_field not in opts.local_fields:
            # This geographic field is inherited from another model, so we have to
            # use the db table for the _parent_ model instead.
            parent_model = geo_field.model._meta.concrete_model
            return self._field_column(compiler, geo_field, parent_model._meta.db_table)
        else:
            return self._field_column(compiler, geo_field)

    # Private API utilities, subject to change.
    def _geo_field(self, field_name=None):
        """
        Returns the first Geometry field encountered or the one specified via
        the `field_name` keyword. The `field_name` may be a string specifying
        the geometry field on this GeoQuerySet's model, or a lookup string
        to a geometry field via a ForeignKey relation.
        """
        if field_name is None:
            # Incrementing until the first geographic field is found.
            for field in self.model._meta.fields:
                if isinstance(field, GeometryField):
                    return field
            return False
        else:
            # Otherwise, check by the given field name -- which may be
            # a lookup to a _related_ geographic field.
            return GISLookup._check_geo_field(self.model._meta, field_name)

    def _field_column(self, compiler, field, table_alias=None, column=None):
        """
        Helper function that returns the database column for the given field.
        The table and column are returned (quoted) in the proper format, e.g.,
        `"geoapp_city"."point"`.  If `table_alias` is not specified, the
        database table associated with the model of this `GeoQuerySet` will be
        used.  If `column` is specified, it will be used instead of the value
        in `field.column`.
        """
        if table_alias is None:
            table_alias = compiler.query.get_meta().db_table
        return "%s.%s" % (compiler.quote_name_unless_alias(table_alias),
                          compiler.connection.ops.quote_name(column or field.column))
