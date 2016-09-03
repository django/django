/*global MapWidget*/

document.addEventListener("DOMContentLoaded", function(event) {
    'use strict';
    var divs = document.querySelectorAll("div.geodjangoDivMap");
    for (var i = 0; i < divs.length; ++i) {
        var options = {
            geom_name: divs[i].getAttribute('data-gis-geomname'),
            id: divs[i].getAttribute('data-gis-id'),
            map_id: divs[i].getAttribute('data-gis-id') + '_map',
            map_options: {},
            map_srid: divs[i].getAttribute('data-gis-mapsrid'),
            name: divs[i].getAttribute('data-gis-name')
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
