(function() {
/**
 * Transforms an array of features to a single feature with the merged
 * geometry of geom_type
 */
OpenLayers.Util.properFeatures = function(features, geom_type) {
    if (features.constructor == Array) {
        var geoms = [];
        for (var i=0; i<features.length; i++) {
            geoms.push(features[i].geometry);
        }
        var geom = new geom_type(geoms);
        features = new OpenLayers.Feature.Vector(geom);
    }
    return features;
}

/**
 * @requires OpenLayers/Format/WKT.js
 */

/**
 * Class: OpenLayers.Format.DjangoWKT
 * Class for reading Well-Known Text, with workarounds to successfully parse
 * geometries and collections as returnes by django.contrib.gis.geos.
 *
 * Inherits from:
 *  - <OpenLayers.Format.WKT>
 */

OpenLayers.Format.DjangoWKT = OpenLayers.Class(OpenLayers.Format.WKT, {
    initialize: function(options) {
        OpenLayers.Format.WKT.prototype.initialize.apply(this, [options]);
        this.regExes.justComma = /\s*,\s*/;
    },

    parse: {
        'point': function(str) {
            var coords = OpenLayers.String.trim(str).split(this.regExes.spaces);
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.Point(coords[0], coords[1])
            );
        },

        'multipoint': function(str) {
            var point;
            var points = OpenLayers.String.trim(str).split(this.regExes.justComma);
            var components = [];
            for(var i=0, len=points.length; i<len; ++i) {
                point = points[i].replace(this.regExes.trimParens, '$1');
                components.push(this.parse.point.apply(this, [point]).geometry);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.MultiPoint(components)
            );
        },

        'linestring': function(str) {
            var points = OpenLayers.String.trim(str).split(',');
            var components = [];
            for(var i=0, len=points.length; i<len; ++i) {
                components.push(this.parse.point.apply(this, [points[i]]).geometry);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.LineString(components)
            );
        },

        'multilinestring': function(str) {
            var line;
            var lines = OpenLayers.String.trim(str).split(this.regExes.parenComma);
            var components = [];
            for(var i=0, len=lines.length; i<len; ++i) {
                line = lines[i].replace(this.regExes.trimParens, '$1');
                components.push(this.parse.linestring.apply(this, [line]).geometry);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.MultiLineString(components)
            );
        },

        'polygon': function(str) {
            var ring, linestring, linearring;
            var rings = OpenLayers.String.trim(str).split(this.regExes.parenComma);
            var components = [];
            for(var i=0, len=rings.length; i<len; ++i) {
                ring = rings[i].replace(this.regExes.trimParens, '$1');
                linestring = this.parse.linestring.apply(this, [ring]).geometry;
                linearring = new OpenLayers.Geometry.LinearRing(linestring.components);
                components.push(linearring);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.Polygon(components)
            );
        },

        'multipolygon': function(str) {
            var polygon;
            var polygons = OpenLayers.String.trim(str).split(this.regExes.doubleParenComma);
            var components = [];
            for(var i=0, len=polygons.length; i<len; ++i) {
                polygon = polygons[i].replace(this.regExes.trimParens, '$1');
                components.push(this.parse.polygon.apply(this, [polygon]).geometry);
            }
            return new OpenLayers.Feature.Vector(
                new OpenLayers.Geometry.MultiPolygon(components)
            );
        },

        'geometrycollection': function(str) {
            // separate components of the collection with |
            str = str.replace(/,\s*([A-Za-z])/g, '|$1');
            var wktArray = OpenLayers.String.trim(str).split('|');
            var components = [];
            for(var i=0, len=wktArray.length; i<len; ++i) {
                components.push(OpenLayers.Format.WKT.prototype.read.apply(this,[wktArray[i]]));
            }
            return components;
        }
    },

    extractGeometry: function(geometry) {
        var type = geometry.CLASS_NAME.split('.')[2].toLowerCase();
        if (!this.extract[type]) {
            return null;
        }
        if (this.internalProjection && this.externalProjection) {
            geometry = geometry.clone();
            geometry.transform(this.internalProjection, this.externalProjection);
        }
        var wktType = type == 'collection' ? 'GEOMETRYCOLLECTION' : type.toUpperCase();
        var data = wktType + '(' + this.extract[type].apply(this, [geometry]) + ')';
        return data;
    },

    /**
     * Patched write: successfully writes WKT for geometries and
     * geometrycollections.
     */
    write: function(features) {
        var collection, geometry, type, data, isCollection;
        isCollection = features.geometry.CLASS_NAME == "OpenLayers.Geometry.Collection";
        var pieces = [];
        if (isCollection) {
            collection = features.geometry.components;
            pieces.push('GEOMETRYCOLLECTION(');
            for (var i=0, len=collection.length; i<len; ++i) {
                if (i>0) {
                    pieces.push(',');
                }
                pieces.push(this.extractGeometry(collection[i]));
            }
            pieces.push(')');
        } else {
            pieces.push(this.extractGeometry(features.geometry));
        }
        return pieces.join('');
    },

    CLASS_NAME: "OpenLayers.Format.DjangoWKT"
});

function MapWidget(options) {
    this.map = null;
    this.controls = null;
    this.panel = null;
    this.layers = {};
    this.wkt_f = new OpenLayers.Format.DjangoWKT();

    // Mapping from OGRGeomType name to OpenLayers.Geometry name
    if (options['geom_name'] == 'Unknown') options['geom_type'] = OpenLayers.Geometry;
    else if (options['geom_name'] == 'GeometryCollection') options['geom_type'] = OpenLayers.Geometry.Collection;
    else options['geom_type'] = eval('OpenLayers.Geometry' + options['geom_name']);

    // Default options
    this.options = {
        color: 'ee9900',
        default_lat: 0,
        default_lon: 0,
        default_zoom: 4,
        is_collection: options['geom_type'] instanceof OpenLayers.Geometry.Collection,
        layerswitcher: false,
        map_options: {},
        map_srid: 4326,
        modifiable: true,
        mouse_position: false,
        opacity: 0.4,
        point_zoom: 12,
        scale_text: false,
        scrollable: true
    };

    // Altering using user-provied options
    for (var property in options) {
        if (options.hasOwnProperty(property)) {
            this.options[property] = options[property];
        }
    }

    this.map = this.create_map();

    var defaults_style = {
        'fillColor': '#' + this.options.color,
        'fillOpacity': this.options.opacity,
        'strokeColor': '#' + this.options.color,
    };
    if (this.options.geom_name == 'LineString') {
        defaults_style['strokeWidth'] = 3;
    }
    var styleMap = new OpenLayers.StyleMap({'default': OpenLayers.Util.applyDefaults(defaults_style, OpenLayers.Feature.Vector.style['default'])});
    this.layers.vector = new OpenLayers.Layer.Vector(" " + this.options.name, {styleMap: styleMap});
    this.map.addLayer(this.layers.vector);
    var wkt = document.getElementById(this.options.id).value;
    if (wkt) {
        var feat = OpenLayers.Util.properFeatures(this.read_wkt(wkt), this.options.geom_type);
        this.write_wkt(feat);
        if (this.options.is_collection) {
            for (var i=0; i<this.num_geom; i++) {
                this.layers.vector.addFeatures([new OpenLayers.Feature.Vector(feat.geometry.components[i].clone())]);
            }
        } else {
            this.layers.vector.addFeatures([feat]);
        }
        this.map.zoomToExtent(feat.geometry.getBounds());
        if (this.options.geom_name == 'Point') {
            this.map.zoomTo(this.options.point_zoom);
        }
    } else {
        this.map.setCenter(this.defaultCenter(), this.options.default_zoom);
    }
    this.layers.vector.events.on({'featuremodified': this.modify_wkt, scope: this});
    this.layers.vector.events.on({'featureadded': this.add_wkt, scope: this});

    this.getControls(this.layers.vector);
    this.panel.addControls(this.controls);
    this.map.addControl(this.panel);
    this.addSelectControl();

    if (this.options.mouse_position) {
        this.map.addControl(new OpenLayers.Control.MousePosition());
    }
    if (this.options.scale_text) {
        this.map.addControl(new OpenLayers.Control.Scale());
    }
    if (this.options.layerswitcher) {
        this.map.addControl(new OpenLayers.Control.LayerSwitcher());
    }
    if (!this.options.scrollable) {
        this.map.getControlsByClass('OpenLayers.Control.Navigation')[0].disableZoomWheel();
    }
    if (wkt) {
        if (this.options.modifiable) {
            this.enableEditing();
        }
    } else {
        this.enableDrawing();
    }
}

MapWidget.prototype.create_map = function() {
    var map = new OpenLayers.Map(this.options.map_id, this.options.map_options);
    if (this.options.base_layer) this.layers.base = this.options.base_layer;
    else this.layers.base = new OpenLayers.Layer.WMS('OpenLayers WMS', 'http://vmap0.tiles.osgeo.org/wms/vmap0', {layers: 'basic'});
    map.addLayer(this.layers.base);
    return map
};

MapWidget.prototype.get_ewkt = function(feat) {
    return "SRID=" + this.options.map_srid + ";" + this.wkt_f.write(feat);
};

MapWidget.prototype.read_wkt = function(wkt) {
    var prefix = 'SRID=' + this.options.map_srid + ';'
    if (wkt.indexOf(prefix) === 0) {
        wkt = wkt.slice(prefix.length);
    }
    return this.wkt_f.read(wkt);
};

MapWidget.prototype.write_wkt = function(feat) {
    feat = OpenLayers.Util.properFeatures(feat, this.options.geom_type);
    if (this.options.is_collection) {
        this.num_geom = feat.geometry.components.length;
    } else {
        this.num_geom = 1;
    }
    document.getElementById(this.options.id).value = this.get_ewkt(feat);
};

MapWidget.prototype.add_wkt = function(event) {
    if (this.options.is_collection) {
        var feat = new OpenLayers.Feature.Vector(new this.options.geom_type());
        for (var i=0; i<this.layers.vector.features.length; i++) {
            feat.geometry.addComponents([this.layers.vector.features[i].geometry]);
        }
        this.write_wkt(feat);
    } else {
        if (this.layers.vector.features.length > 1) {
            old_feats = [this.layers.vector.features[0]];
            this.layers.vector.removeFeatures(old_feats);
            this.layers.vector.destroyFeatures(old_feats);
        }
        this.write_wkt(event.feature);
    }
};

MapWidget.prototype.modify_wkt = function(event) {
    if (this.options.is_collection) {
        if (this.options.geom_name == 'MultiPoint') {
            this.add_wkt(event);
            return;
        } else {
            var feat = new OpenLayers.Feature.Vector(new this.options.geom_type());
            for (var i=0; i<this.num_geom; i++) {
                feat.geometry.addComponents([this.layers.vector.features[i].geometry]);
            }
            this.write_wkt(feat);
        }
    } else {
        this.write_wkt(event.feature);
    }
};

MapWidget.prototype.deleteFeatures = function() {
    this.layers.vector.removeFeatures(this.layers.vector.features);
    this.layers.vector.destroyFeatures();
};

MapWidget.prototype.clearFeatures = function() {
    this.deleteFeatures();
    document.getElementById(this.options.id).value = '';
    this.map.setCenter(this.defaultCenter(), this.options.default_zoom);
};

MapWidget.prototype.defaultCenter = function() {
    var center = new OpenLayers.LonLat(this.options.default_lon, this.options.default_lat);
    if (this.options.map_srid) {
        return center.transform(new OpenLayers.Projection("EPSG:4326"), this.map.getProjectionObject());
    }
    return center;
};

MapWidget.prototype.addSelectControl = function() {
    var select = new OpenLayers.Control.SelectFeature(this.layers.vector, {'toggle': true, 'clickout': true});
    this.map.addControl(select);
    select.activate();
};

MapWidget.prototype.enableDrawing = function () {
    this.map.getControlsByClass('OpenLayers.Control.DrawFeature')[0].activate();
};

MapWidget.prototype.enableEditing = function () {
    this.map.getControlsByClass('OpenLayers.Control.ModifyFeature')[0].activate();
};

MapWidget.prototype.getControls = function(layer) {
    this.panel = new OpenLayers.Control.Panel({'displayClass': 'olControlEditingToolbar'});
    this.controls = [new OpenLayers.Control.Navigation()];
    if (!this.options.modifiable && layer.features.length)
        return;
    if (this.options.geom_name == 'LineString' || this.options.geom_name == 'Unknown') {
        this.controls.push(new OpenLayers.Control.DrawFeature(layer, OpenLayers.Handler.Path, {'displayClass': 'olControlDrawFeaturePath'}));
    }
    if (this.options.geom_name == 'Polygon' || this.options.geom_name == 'Unknown') {
        this.controls.push(new OpenLayers.Control.DrawFeature(layer, OpenLayers.Handler.Polygon, {'displayClass': 'olControlDrawFeaturePolygon'}));
    }
    if (this.options.geom_name == 'Point' || this.options.geom_name == 'Unknown') {
        this.controls.push(new OpenLayers.Control.DrawFeature(layer, OpenLayers.Handler.Point, {'displayClass': 'olControlDrawFeaturePoint'}));
    }
    if (this.options.modifiable) {
        this.controls.push(new OpenLayers.Control.ModifyFeature(layer, {'displayClass': 'olControlModifyFeature'}));
    }
};
window.MapWidget = MapWidget;
})();
