/* global ol */
'use strict';
function GeometryTypeControl(opt_options) {
    // Map control to switch type when geometry type is unknown
    const options = opt_options || {};

    const element = document.createElement('div');
    element.className = 'switch-type type-' + options.type + ' ol-control ol-unselectable';
    if (options.active) {
        element.classList.add("type-active");
    }

    const self = this;
    const switchType = function(e) {
        e.preventDefault();
        if (options.widget.currentGeometryType !== self) {
            options.widget.map.removeInteraction(options.widget.interactions.draw);
            options.widget.interactions.draw = new ol.interaction.Draw({
                features: options.widget.featureCollection,
                type: options.type
            });
            options.widget.map.addInteraction(options.widget.interactions.draw);
            options.widget.currentGeometryType.element.classList.remove('type-active');
            options.widget.currentGeometryType = self;
            element.classList.add("type-active");
        }
    };

    element.addEventListener('click', switchType, false);
    element.addEventListener('touchstart', switchType, false);

    ol.control.Control.call(this, {
        element: element
    });
};
ol.inherits(GeometryTypeControl, ol.control.Control);

// TODO: allow deleting individual features (#8972)
class MapWidget {
    constructor(options) {
        this.map = null;
        this.interactions = {draw: null, modify: null};
        this.typeChoices = false;
        this.ready = false;

        // Default options
        this.options = {
            default_lat: 0,
            default_lon: 0,
            default_zoom: 12,
            is_collection: options.geom_name.includes('Multi') || options.geom_name.includes('Collection')
        };

        // Altering using user-provided options
        for (const property in options) {
            if (options.hasOwnProperty(property)) {
                this.options[property] = options[property];
            }
        }
        if (!options.base_layer) {
            this.options.base_layer = new ol.layer.Tile({source: new ol.source.OSM()});
        }

        // RemovedInDjango51Warning: when the deprecation ends, remove setting
        // width/height (3 lines below).
        const mapContainer = document.getElementById(this.options.map_id);
        mapContainer.style.width = `${mapContainer.dataset.width}px`;
        mapContainer.style.height = `${mapContainer.dataset.height}px`;
        this.map = this.createMap();
        this.featureCollection = new ol.Collection();
        this.featureOverlay = new ol.layer.Vector({
            map: this.map,
            source: new ol.source.Vector({
                features: this.featureCollection,
                useSpatialIndex: false // improve performance
            }),
            updateWhileAnimating: true, // optional, for instant visual feedback
            updateWhileInteracting: true // optional, for instant visual feedback
        });

        // Populate and set handlers for the feature container
        const self = this;
        this.featureCollection.on('add', function(event) {
            const feature = event.element;
            feature.on('change', function() {
                self.serializeFeatures();
            });
            if (self.ready) {
                self.serializeFeatures();
                if (!self.options.is_collection) {
                    self.disableDrawing(); // Only allow one feature at a time
                }
            }
        });

        const initial_value = document.getElementById(this.options.id).value;
        if (initial_value) {
            const jsonFormat = new ol.format.GeoJSON();
            const features = jsonFormat.readFeatures('{"type": "Feature", "geometry": ' + initial_value + '}');
            const extent = ol.extent.createEmpty();
            features.forEach(function(feature) {
                this.featureOverlay.getSource().addFeature(feature);
                ol.extent.extend(extent, feature.getGeometry().getExtent());
            }, this);
            // Center/zoom the map
            this.map.getView().fit(extent, {minResolution: 1});
        } else {
            this.map.getView().setCenter(this.defaultCenter());
        }
        this.createInteractions();
        if (initial_value && !this.options.is_collection) {
            this.disableDrawing();
        }
        const clearNode = document.getElementById(this.map.getTarget()).nextElementSibling;
        if (clearNode.classList.contains('clear_features')) {
            clearNode.querySelector('a').addEventListener('click', (ev) => {
                ev.preventDefault();
                self.clearFeatures();
            });
        }
        this.ready = true;
    }

    createMap() {
        return new ol.Map({
            target: this.options.map_id,
            layers: [this.options.base_layer],
            view: new ol.View({
                zoom: this.options.default_zoom
            })
        });
    }

    createInteractions() {
        // Initialize the modify interaction
        this.interactions.modify = new ol.interaction.Modify({
            features: this.featureCollection,
            deleteCondition: function(event) {
                return ol.events.condition.shiftKeyOnly(event) &&
                    ol.events.condition.singleClick(event);
            }
        });

        // Initialize the draw interaction
        let geomType = this.options.geom_name;
        if (geomType === "Geometry" || geomType === "GeometryCollection") {
            // Default to Point, but create icons to switch type
            geomType = "Point";
            this.currentGeometryType = new GeometryTypeControl({widget: this, type: "Point", active: true});
            this.map.addControl(this.currentGeometryType);
            this.map.addControl(new GeometryTypeControl({widget: this, type: "LineString", active: false}));
            this.map.addControl(new GeometryTypeControl({widget: this, type: "Polygon", active: false}));
            this.typeChoices = true;
        }
        this.interactions.draw = new ol.interaction.Draw({
            features: this.featureCollection,
            type: geomType
        });

        this.map.addInteraction(this.interactions.draw);
        this.map.addInteraction(this.interactions.modify);
    }

    defaultCenter() {
        const center = [this.options.default_lon, this.options.default_lat];
        if (this.options.map_srid) {
            return ol.proj.transform(center, 'EPSG:4326', this.map.getView().getProjection());
        }
        return center;
    }

    enableDrawing() {
        this.interactions.draw.setActive(true);
        if (this.typeChoices) {
            // Show geometry type icons
            const divs = document.getElementsByClassName("switch-type");
            for (let i = 0; i !== divs.length; i++) {
                divs[i].style.visibility = "visible";
            }
        }
    }

    disableDrawing() {
        if (this.interactions.draw) {
            this.interactions.draw.setActive(false);
            if (this.typeChoices) {
                // Hide geometry type icons
                const divs = document.getElementsByClassName("switch-type");
                for (let i = 0; i !== divs.length; i++) {
                    divs[i].style.visibility = "hidden";
                }
            }
        }
    }

    clearFeatures() {
        this.featureCollection.clear();
        // Empty textarea widget
        document.getElementById(this.options.id).value = '';
        this.enableDrawing();
    }

    serializeFeatures() {
        // Three use cases: GeometryCollection, multigeometries, and single geometry
        let geometry = null;
        const features = this.featureOverlay.getSource().getFeatures();
        if (this.options.is_collection) {
            if (this.options.geom_name === "GeometryCollection") {
                const geometries = [];
                for (let i = 0; i < features.length; i++) {
                    geometries.push(features[i].getGeometry());
                }
                geometry = new ol.geom.GeometryCollection(geometries);
            } else {
                geometry = features[0].getGeometry().clone();
                for (let j = 1; j < features.length; j++) {
                    switch (geometry.getType()) {
                    case "MultiPoint":
                        geometry.appendPoint(features[j].getGeometry().getPoint(0));
                        break;
                    case "MultiLineString":
                        geometry.appendLineString(features[j].getGeometry().getLineString(0));
                        break;
                    case "MultiPolygon":
                        geometry.appendPolygon(features[j].getGeometry().getPolygon(0));
                    }
                }
            }
        } else {
            if (features[0]) {
                geometry = features[0].getGeometry();
            }
        }
        const jsonFormat = new ol.format.GeoJSON();
        document.getElementById(this.options.id).value = jsonFormat.writeGeometry(geometry);
    }
}
