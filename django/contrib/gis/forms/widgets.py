import logging

from django.contrib.gis import gdal
from django.contrib.gis.geometry import json_regex
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.forms.widgets import Widget

logger = logging.getLogger("django.contrib.gis")


class BaseGeometryWidget(Widget):
    """
    The base class for rich geometry widgets.
    Render a map using the WKT of the geometry.
    """

    base_layer_name = None
    geom_type = "GEOMETRY"
    map_srid = 4326
    display_raw = False

    supports_3d = False
    template_name = ""  # set on subclasses

    def __init__(self, attrs=None):
        self.attrs = {}
        for key in ("geom_type", "map_srid", "display_raw"):
            self.attrs[key] = getattr(self, key)
        if attrs:
            self.attrs.update(attrs)

    def serialize(self, value):
        return value.wkt if value else ""

    def deserialize(self, value):
        try:
            return GEOSGeometry(value)
        except (GEOSException, ValueError, TypeError) as err:
            logger.error("Error creating geometry from value '%s' (%s)", value, err)
        return None

    def widget_options(self):
        """Return options that are passed to the JS MapWidget constructor.

        These options control how the geometry widget behaves in the browser.
        Result is a dictionary with relevant options. Typical entries include:

        * `base_layer`: the name of the base map layer to use (e.g., "osm").
        * `geom_name`: the name/type of geometry (like "Point" or "Polygon").
        * `map_srid`: the spatial reference ID the map should use.

        Subclasses may override or extend it to include additional options
        like default zoom or center.

        """
        geom_type = gdal.OGRGeomType(self.attrs["geom_type"]).name
        return {
            "base_layer": self.base_layer_name,
            "geom_name": "Geometry" if geom_type == "Unknown" else geom_type,
            "map_srid": self.attrs["map_srid"],
        }

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # If a string reaches here (via a validation error on another
        # field) then just reconstruct the Geometry.
        if value and isinstance(value, str):
            value = self.deserialize(value)

        if value:
            # Check that srid of value and map match
            if value.srid and value.srid != self.map_srid:
                try:
                    ogr = value.ogr
                    ogr.transform(self.map_srid)
                    value = ogr
                except gdal.GDALException as err:
                    logger.error(
                        "Error transforming geometry from srid '%s' to srid '%s' (%s)",
                        value.srid,
                        self.map_srid,
                        err,
                    )
        context.update(
            {
                "serialized": self.serialize(value),
                "widget_options": self.widget_options(),
            }
        )
        return context


class OpenLayersWidget(BaseGeometryWidget):
    base_layer_name = "nasaWorldview"
    template_name = "gis/openlayers.html"
    map_srid = 3857

    class Media:
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/ol@v7.2.2/ol.css",
                "gis/css/ol3.css",
            )
        }
        js = (
            "https://cdn.jsdelivr.net/npm/ol@v7.2.2/dist/ol.js",
            "gis/js/OLMapWidget.js",
        )

    def serialize(self, value):
        return value.json if value else ""

    def deserialize(self, value):
        geom = super().deserialize(value)
        # GeoJSON assumes WGS84 (4326). Use the map's SRID instead.
        if geom and json_regex.match(value) and self.map_srid != 4326:
            geom.srid = self.map_srid
        return geom


class OSMWidget(OpenLayersWidget):
    """
    An OpenLayers/OpenStreetMap-based widget.
    """

    base_layer_name = "osm"
    default_lon = 5
    default_lat = 47
    default_zoom = 12

    def __init__(self, attrs=None):
        super().__init__()
        for key in ("default_lon", "default_lat", "default_zoom"):
            self.attrs[key] = getattr(self, key)
        if attrs:
            self.attrs.update(attrs)

    def widget_options(self):
        return {
            **super().widget_options(),
            "default_lon": self.attrs.get("default_lon", self.default_lon),
            "default_lat": self.attrs.get("default_lat", self.default_lat),
            "default_zoom": self.attrs.get("default_zoom", self.default_zoom),
        }
