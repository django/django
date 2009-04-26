from django.conf import settings
from django.contrib.admin import ModelAdmin
from django.contrib.gis.admin.widgets import OpenLayersWidget
from django.contrib.gis.gdal import OGRGeomType
from django.contrib.gis.db import models

class GeoModelAdmin(ModelAdmin):
    """
    The administration options class for Geographic models. Map settings
    may be overloaded from their defaults to create custom maps.
    """
    # The default map settings that may be overloaded -- still subject
    # to API changes.
    default_lon = 0
    default_lat = 0
    default_zoom = 4
    display_wkt = False
    display_srid = False
    extra_js = []
    num_zoom = 18
    max_zoom = False
    min_zoom = False
    units = False
    max_resolution = False
    max_extent = False
    modifiable = True
    mouse_position = True
    scale_text = True
    layerswitcher = True
    scrollable = True
    map_width = 600
    map_height = 400
    map_srid = 4326
    map_template = 'gis/admin/openlayers.html'
    openlayers_url = 'http://openlayers.org/api/2.7/OpenLayers.js'
    point_zoom = num_zoom - 6
    wms_url = 'http://labs.metacarta.com/wms/vmap0'
    wms_layer = 'basic'
    wms_name = 'OpenLayers WMS'
    debug = False
    widget = OpenLayersWidget

    def _media(self):
        "Injects OpenLayers JavaScript into the admin."
        media = super(GeoModelAdmin, self)._media()
        media.add_js([self.openlayers_url])
        media.add_js(self.extra_js)
        return media
    media = property(_media)

    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Overloaded from ModelAdmin so that an OpenLayersWidget is used
        for viewing/editing GeometryFields.
        """
        if isinstance(db_field, models.GeometryField):
            request = kwargs.pop('request', None)
            # Setting the widget with the newly defined widget.
            kwargs['widget'] = self.get_map_widget(db_field)
            return db_field.formfield(**kwargs)
        else:
            return super(GeoModelAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def get_map_widget(self, db_field):
        """
        Returns a subclass of the OpenLayersWidget (or whatever was specified
        in the `widget` attribute) using the settings from the attributes set 
        in this class.
        """
        is_collection = db_field.geom_type in ('MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON', 'GEOMETRYCOLLECTION')
        if is_collection:
            if db_field.geom_type == 'GEOMETRYCOLLECTION': collection_type = 'Any'
            else: collection_type = OGRGeomType(db_field.geom_type.replace('MULTI', ''))
        else:
            collection_type = 'None'

        class OLMap(self.widget):
            template = self.map_template
            geom_type = db_field.geom_type
            params = {'default_lon' : self.default_lon,
                      'default_lat' : self.default_lat,
                      'default_zoom' : self.default_zoom,
                      'display_wkt' : self.debug or self.display_wkt,
                      'geom_type' : OGRGeomType(db_field.geom_type),
                      'field_name' : db_field.name,
                      'is_collection' : is_collection,
                      'scrollable' : self.scrollable,
                      'layerswitcher' : self.layerswitcher,
                      'collection_type' : collection_type,
                      'is_linestring' : db_field.geom_type in ('LINESTRING', 'MULTILINESTRING'),
                      'is_polygon' : db_field.geom_type in ('POLYGON', 'MULTIPOLYGON'),
                      'is_point' : db_field.geom_type in ('POINT', 'MULTIPOINT'),
                      'num_zoom' : self.num_zoom,
                      'max_zoom' : self.max_zoom,
                      'min_zoom' : self.min_zoom,
                      'units' : self.units, #likely shoud get from object
                      'max_resolution' : self.max_resolution,
                      'max_extent' : self.max_extent,
                      'modifiable' : self.modifiable,
                      'mouse_position' : self.mouse_position,
                      'scale_text' : self.scale_text,
                      'map_width' : self.map_width,
                      'map_height' : self.map_height,
                      'point_zoom' : self.point_zoom,
                      'srid' : self.map_srid,
                      'display_srid' : self.display_srid,
                      'wms_url' : self.wms_url,
                      'wms_layer' : self.wms_layer,
                      'wms_name' : self.wms_name,
                      'debug' : self.debug,
                      }
        return OLMap

# Using the Beta OSM in the admin requires the following:
#  (1) The Google Maps Mercator projection needs to be added
#      to your `spatial_ref_sys` table.  You'll need at least GDAL 1.5:
#      >>> from django.contrib.gis.gdal import SpatialReference
#      >>> from django.contrib.gis.utils import add_postgis_srs
#      >>> add_postgis_srs(SpatialReference(900913)) # Adding the Google Projection 
from django.contrib.gis import gdal
if gdal.HAS_GDAL:
    class OSMGeoAdmin(GeoModelAdmin):
        map_template = 'gis/admin/osm.html'
        extra_js = ['http://openstreetmap.org/openlayers/OpenStreetMap.js']
        num_zoom = 20
        map_srid = 900913
        max_extent = '-20037508,-20037508,20037508,20037508'
        max_resolution = 156543.0339
        point_zoom = num_zoom - 6
        units = 'm'
