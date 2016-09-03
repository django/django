/*global OpenLayers, MapWidget*/

document.addEventListener("DOMContentLoaded", function(event) {
    'use strict';
    var map_options = {
        maxExtend: new OpenLayers.Bounds(-20037508, -20037508, 20037508, 20037508),
        maxResolution: 156543.0339,
        numZoomLevels: 20,
        units: 'm'
    };
    var divs = document.querySelectorAll("div.geodjangoDivMapOSM");
    for (var i = 0; i < divs.length; ++i) {
        var options = {
            geom_name: divs[i].getAttribute('data-gis-geomname'),
            id: divs[i].getAttribute('data-gis-id'),
            map_id: divs[i].getAttribute('data-gis-id') + '_map',
            map_options: map_options,
            map_srid: divs[i].getAttribute('data-gis-mapsrid'),
            name: divs[i].getAttribute('data-gis-name'),
            // OSM-specific
            scale_text: true,
            mouse_position: true,
            base_layer: new OpenLayers.Layer.OSM("OpenStreetMap (Mapnik)"),
            default_lon: divs[i].getAttribute('data-gis-defaultlon'),
            default_lat: divs[i].getAttribute('data-gis-defaultlat')
        };
        var widget = new MapWidget(options);
        var clear = divs[i].querySelector('span.clear_features');
        if (clear) {
            clear.addEventListener("click", function(ev) {
                widget.clearFeatures();
            });
        }
    }
});
