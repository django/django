# RemovedInDjango50Warning.
import logging
import warnings

from django.contrib.gis.gdal import GDALException
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.forms.widgets import Textarea
from django.utils import translation
from django.utils.deprecation import RemovedInDjango50Warning

# Creating a template context that contains Django settings
# values needed by admin map templates.
geo_context = {"LANGUAGE_BIDI": translation.get_language_bidi()}
logger = logging.getLogger("django.contrib.gis")


class OpenLayersWidget(Textarea):
    """
    Render an OpenLayers map using the WKT of the geometry.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "django.contrib.gis.admin.OpenLayersWidget is deprecated.",
            RemovedInDjango50Warning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        # Update the template parameters with any attributes passed in.
        if attrs:
            self.params.update(attrs)
            self.params["editable"] = self.params["modifiable"]
        else:
            self.params["editable"] = True

        # Defaulting the WKT value to a blank string -- this
        # will be tested in the JavaScript and the appropriate
        # interface will be constructed.
        self.params["wkt"] = ""

        # If a string reaches here (via a validation error on another
        # field) then just reconstruct the Geometry.
        if value and isinstance(value, str):
            try:
                value = GEOSGeometry(value)
            except (GEOSException, ValueError) as err:
                logger.error("Error creating geometry from value '%s' (%s)", value, err)
                value = None

        if (
            value
            and value.geom_type.upper() != self.geom_type
            and self.geom_type != "GEOMETRY"
        ):
            value = None

        # Constructing the dictionary of the map options.
        self.params["map_options"] = self.map_options()

        # Constructing the JavaScript module name using the name of
        # the GeometryField (passed in via the `attrs` keyword).
        # Use the 'name' attr for the field name (rather than 'field')
        self.params["name"] = name
        # note: we must switch out dashes for underscores since js
        # functions are created using the module variable
        js_safe_name = self.params["name"].replace("-", "_")
        self.params["module"] = "geodjango_%s" % js_safe_name

        if value:
            # Transforming the geometry to the projection used on the
            # OpenLayers map.
            srid = self.params["srid"]
            if value.srid != srid:
                try:
                    ogr = value.ogr
                    ogr.transform(srid)
                    wkt = ogr.wkt
                except GDALException as err:
                    logger.error(
                        "Error transforming geometry from srid '%s' to srid '%s' (%s)",
                        value.srid,
                        srid,
                        err,
                    )
                    wkt = ""
            else:
                wkt = value.wkt

            # Setting the parameter WKT with that of the transformed
            # geometry.
            self.params["wkt"] = wkt

        self.params.update(geo_context)
        return self.params

    def map_options(self):
        """Build the map options hash for the OpenLayers template."""

        # JavaScript construction utilities for the Bounds and Projection.
        def ol_bounds(extent):
            return "new OpenLayers.Bounds(%s)" % extent

        def ol_projection(srid):
            return 'new OpenLayers.Projection("EPSG:%s")' % srid

        # An array of the parameter name, the name of their OpenLayers
        # counterpart, and the type of variable they are.
        map_types = [
            ("srid", "projection", "srid"),
            ("display_srid", "displayProjection", "srid"),
            ("units", "units", str),
            ("max_resolution", "maxResolution", float),
            ("max_extent", "maxExtent", "bounds"),
            ("num_zoom", "numZoomLevels", int),
            ("max_zoom", "maxZoomLevels", int),
            ("min_zoom", "minZoomLevel", int),
        ]

        # Building the map options hash.
        map_options = {}
        for param_name, js_name, option_type in map_types:
            if self.params.get(param_name, False):
                if option_type == "srid":
                    value = ol_projection(self.params[param_name])
                elif option_type == "bounds":
                    value = ol_bounds(self.params[param_name])
                elif option_type in (float, int):
                    value = self.params[param_name]
                elif option_type in (str,):
                    value = '"%s"' % self.params[param_name]
                else:
                    raise TypeError
                map_options[js_name] = value
        return map_options
