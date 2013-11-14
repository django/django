import logging

from django.forms.widgets import Textarea
from django.template import loader, Context
from django.utils import six
from django.utils import translation

from django.contrib.gis.gdal import OGRException
from django.contrib.gis.geos import GEOSGeometry, GEOSException

# Creating a template context that contains Django settings
# values needed by admin map templates.
geo_context = Context({'LANGUAGE_BIDI': translation.get_language_bidi()})
logger = logging.getLogger('django.contrib.gis')


class OpenLayersWidget(Textarea):
    """
    Renders an OpenLayers map using the WKT of the geometry.
    """
    def render(self, name, value, attrs=None):
        # Update the template parameters with any attributes passed in.
        if attrs:
            self.params.update(attrs)

        # Defaulting the WKT value to a blank string -- this
        # will be tested in the JavaScript and the appropriate
        # interface will be constructed.
        self.params['wkt'] = ''

        # If a string reaches here (via a validation error on another
        # field) then just reconstruct the Geometry.
        if isinstance(value, six.string_types):
            try:
                value = GEOSGeometry(value)
            except (GEOSException, ValueError) as err:
                logger.error(
                    "Error creating geometry from value '%s' (%s)" % (
                        value, err)
                )
                value = None

        if (value and value.geom_type.upper() != self.geom_type and
                self.geom_type != 'GEOMETRY'):
            value = None

        # Constructing the dictionary of the map options.
        self.params['map_options'] = self.map_options()

        # Constructing the JavaScript module name using the name of
        # the GeometryField (passed in via the `attrs` keyword).
        # Use the 'name' attr for the field name (rather than 'field')
        self.params['name'] = name
        # note: we must switch out dashes for underscores since js
        # functions are created using the module variable
        js_safe_name = self.params['name'].replace('-', '_')
        self.params['module'] = 'geodjango_%s' % js_safe_name

        if value:
            # Transforming the geometry to the projection used on the
            # OpenLayers map.
            srid = self.params['srid']
            if value.srid != srid:
                try:
                    ogr = value.ogr
                    ogr.transform(srid)
                    wkt = ogr.wkt
                except OGRException as err:
                    logger.error(
                        "Error transforming geometry from srid '%s' to srid '%s' (%s)" % (
                            value.srid, srid, err)
                    )
                    wkt = ''
            else:
                wkt = value.wkt

            # Setting the parameter WKT with that of the transformed
            # geometry.
            self.params['wkt'] = wkt

        return loader.render_to_string(self.template, self.params,
                                       context_instance=geo_context)

    def map_options(self):
        "Builds the map options hash for the OpenLayers template."

        # JavaScript construction utilities for the Bounds and Projection.
        def ol_bounds(extent):
            return 'new OpenLayers.Bounds(%s)' % str(extent)

        def ol_projection(srid):
            return 'new OpenLayers.Projection("EPSG:%s")' % srid

        # An array of the parameter name, the name of their OpenLayers
        # counterpart, and the type of variable they are.
        map_types = [('srid', 'projection', 'srid'),
                     ('display_srid', 'displayProjection', 'srid'),
                     ('units', 'units', str),
                     ('max_resolution', 'maxResolution', float),
                     ('max_extent', 'maxExtent', 'bounds'),
                     ('num_zoom', 'numZoomLevels', int),
                     ('max_zoom', 'maxZoomLevels', int),
                     ('min_zoom', 'minZoomLevel', int),
                     ]

        # Building the map options hash.
        map_options = {}
        for param_name, js_name, option_type in map_types:
            if self.params.get(param_name, False):
                if option_type == 'srid':
                    value = ol_projection(self.params[param_name])
                elif option_type == 'bounds':
                    value = ol_bounds(self.params[param_name])
                elif option_type in (float, int):
                    value = self.params[param_name]
                elif option_type in (str,):
                    value = '"%s"' % self.params[param_name]
                else:
                    raise TypeError
                map_options[js_name] = value
        return map_options
