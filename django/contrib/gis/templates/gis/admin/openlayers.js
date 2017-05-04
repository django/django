{% load l10n %}
OpenLayers.Projection.addTransform("EPSG:4326", "EPSG:3857", OpenLayers.Layer.SphericalMercator.projectForward);
(function (_root) {
    var _moduleName = "{{ module }}";
    var originalOptions = "{{ map_options | json }}";
    var srid = "{{ srid | unlocalize }}";
    var id = "{{ id }}";
    var geomType = "{{ geomType }}";
    var defaultLon = {{ default_lon }};
    var defaultLat = {{ default_lat }};
    var defaultZoom = {{ default_zoom }};
    var wmsName = "{{ wms_name }}";
    var wmsUrl = "{{ wms_url }}";
    var wmsLayer = "{{ wms_layer }}";
    var wmsOptions = {_fakeKey: undefined{{ wms_options | safe}} };
    var isLinestring = {% is_linestring|yesno:"true,false" %};
    var fieldName = "{{ field_name}}";
    var pointZoom = "{{ point_zoom }}";
    var mousePosition = {% mouse_position|yesno: "true,false" %};
    var scaleText = {% scale_text|yesno: "true,false" %};
    var layerswitcher = {% layerswitcher|yesno: "true,false" %};
    var scrollable = {% scrollable|yesno: "true,false" %};
    delete wmsOptions._fakeKey;
    function getModuleVars() {
      {% block vars %}
          var _mod = {};
          var {{ module }} = _module;
          _module.map = null; _module.controls = null; _module.panel = null; _module.re = new RegExp("^SRID=\\d+;(.+)", "i"); _module.layers = {};
          _module.modifiable = {{ modifiable|yesno:"true,false" }};
          _module.wkt_f = new OpenLayers.Format.WKT();
          _module.is_collection = {{ is_collection|yesno:"true,false" }};
          _module.collection_type = '{{ collection_type }}';
          _module.is_generic = {{ is_generic|yesno:"true,false" }};
          _module.is_linestring = isLinestring;
          _module.is_polygon = {{ is_polygon|yesno:"true,false" }};
          _module.is_point = {{ is_point|yesno:"true,false" }};
      {% endblock %}
      // can't return _mod, in case a child template redifines module.
      return {{ module }};
    };

    function getMapOptions() {
        {% block map_options %}// The options hash, w/ zoom, resolution, and projection settings.
            var options = _orignalOptions;
        {% endblock %}
        return options;
    }

    function getBaseLayer() {
        return {% block base_layer %}new OpenLayers.Layer.WMS(wmsName, wmsUrl, wmsOptions);{% endblock %}
    }

    function decorateMap(_mod, options) {
        var {{ module }} = _mod;
        {% block map_creation %}
            _mod.map = new OpenLayers.Map(id + '_map', options);
            // Base Layer
            _mod.layers.base = getBaseLayer();
            _mod.map.addLayer(_module.layers.base);
        {% endblock %}
        {% block extra_layers %}{% endblock %}
    }

    function applyControlls(_mod) {
        var {{ module }} = _mod;
        {% block controls %}
            // Map controls:
            // Add geometry specific panel of toolbar controls
            _mod.getControls(_mod.layers.vector);
            _mod.panel.addControls(_mod.controls);
            _mod.map.addControl(_mod.panel);
            _mod.addSelectControl();
            // Then add optional visual controls
            if (mousePosition) {
                _mod.map.addControl(new OpenLayers.Control.MousePosition());
            }
            if (scaleText) {
                _mod.map.addControl(new OpenLayers.Control.Scale());
            }
            if (layerswitcher) {
                _mod.map.addControl(new OpenLayers.Control.LayerSwitcher());
            }
            // Then add optional behavior controls
            if (!scrollable) {
                _mod.map.getControlsByClass('OpenLayers.Control.Navigation')[0].disableZoomWheel();
            }
        {% endblock %}
    }

    var _module = getModuleVars();
    _module.get_ewkt = function(feat){
        return 'SRID=' + srid + ';' + _module.wkt_f.write(feat);
    };
    _module.read_wkt = function(wkt){
        // OpenLayers cannot handle EWKT -- we make sure to strip it out.
        // EWKT is only exposed to OL if there's a validation error in the admin.
        var match = _module.re.exec(wkt);
        if (match){wkt = match[1];}
        return _module.wkt_f.read(wkt);
    };
    _module.write_wkt = function(feat){
        if (_module.is_collection){ _module.num_geom = feat.geometry.components.length;}
        else { _module.num_geom = 1;}
        document.getElementById(id).value = _module.get_ewkt(feat);
    };
    _module.add_wkt = function(event){
        // This function will sync the contents of the `vector` layer with the
        // WKT in the text field.
        if (_module.is_collection){
            var feat = new OpenLayers.Feature.Vector(new OpenLayers.Geometry[geomType]());
            for (var i = 0; i < _module.layers.vector.features.length; i++){
                feat.geometry.addComponents([_module.layers.vector.features[i].geometry]);
            }
            _module.write_wkt(feat);
        } else {
            // Make sure to remove any previously added features.
            if (_module.layers.vector.features.length > 1){
                old_feats = [_module.layers.vector.features[0]];
                _module.layers.vector.removeFeatures(old_feats);
                _module.layers.vector.destroyFeatures(old_feats);
            }
            _module.write_wkt(event.feature);
        }
    };
    _module.modify_wkt = function(event){
        if (_module.is_collection){
            if (_module.is_point){
                _module.add_wkt(event);
                return;
            } else {
                // When modifying the selected components are added to the
                // vector layer so we only increment to the `num_geom` value.
                var feat = new OpenLayers.Feature.Vector(new OpenLayers.Geometry[geomType]());
                for (var i = 0; i < _module.num_geom; i++){
                    feat.geometry.addComponents([_module.layers.vector.features[i].geometry]);
                }
                _module.write_wkt(feat);
            }
        } else {
            _module.write_wkt(event.feature);
        }
    };
    // Function to clear vector features and purge wkt from div
    _module.deleteFeatures = function(){
        _module.layers.vector.removeFeatures(_module.layers.vector.features);
        _module.layers.vector.destroyFeatures();
    };
    _module.clearFeatures = function (){
        _module.deleteFeatures();
        document.getElementById(id).value = '';
        {% localize off %}
        _module.map.setCenter(new OpenLayers.LonLat(defaultLon, defaultLat), defaultZoom);
        {% endlocalize %}
    };
    // Add Select control
    _module.addSelectControl = function(){
        var select = new OpenLayers.Control.SelectFeature(_module.layers.vector, {'toggle' : true, 'clickout' : true});
        _module.map.addControl(select);
        select.activate();
    };
    _module.enableDrawing = function(){
        _module.map.getControlsByClass('OpenLayers.Control.DrawFeature')[0].activate();
    };
    _module.enableEditing = function(){
        _module.map.getControlsByClass('OpenLayers.Control.ModifyFeature')[0].activate();
    };
    // Create an array of controls based on geometry type
    _module.getControls = function(lyr){
        _module.panel = new OpenLayers.Control.Panel({'displayClass': 'olControlEditingToolbar'});
        _module.controls = [new OpenLayers.Control.Navigation()];
        if (!_module.modifiable && lyr.features.length) return;
        if (_module.is_linestring || _module.is_generic){
            _module.controls.push(new OpenLayers.Control.DrawFeature(lyr, OpenLayers.Handler.Path, {'displayClass': 'olControlDrawFeaturePath'}));
        }
        if (_module.is_polygon || _module.is_generic){
            _module.controls.push(new OpenLayers.Control.DrawFeature(lyr, OpenLayers.Handler.Polygon, {'displayClass': 'olControlDrawFeaturePolygon'}));
        }
        if (_module.is_point || _module.is_generic){
            _module.controls.push(new OpenLayers.Control.DrawFeature(lyr, OpenLayers.Handler.Point, {'displayClass': 'olControlDrawFeaturePoint'}));
        }
        if (_module.modifiable){
            _module.controls.push(new OpenLayers.Control.ModifyFeature(lyr, {'displayClass': 'olControlModifyFeature'}));
        }
    };
    _module.init = function(){
        var options = getMapOptions();
        // The admin map for this geometry field.
        var mapCreated = decorateMap(_module, options);
        if (isLinestring) {
            // Default too thin for linestrings.
            OpenLayers.Feature.Vector.style["default"]["strokeWidth"] = 3;
        }
        _module.layers.vector = new OpenLayers.Layer.Vector(" " + fieldName);
        _module.map.addLayer(_module.layers.vector);
        // Read WKT from the text field.
        var wkt = document.getElementById(id).value;
        if (wkt){
            // After reading into geometry, immediately write back to
            // WKT <textarea> as EWKT (so that SRID is included).
            var admin_geom = _module.read_wkt(wkt);
            _module.write_wkt(admin_geom);
            if (_module.is_collection){
                // If geometry collection, add each component individually so they may be
                // edited individually.
                for (var i = 0; i < _module.num_geom; i++){
                    _module.layers.vector.addFeatures([new OpenLayers.Feature.Vector(admin_geom.geometry.components[i].clone())]);
                }
            } else {
                _module.layers.vector.addFeatures([admin_geom]);
            }
            // Zooming to the bounds.
            _module.map.zoomToExtent(admin_geom.geometry.getBounds());
            if (_module.is_point){
                _module.map.zoomTo(Number(pointZoom));
            }
        } else {
            _module.map.setCenter(new OpenLayers.LonLat(defaultLon, defaultLat), defaultZoom);
        }
        applyControls(_module);
        // This allows editing of the geographic fields -- the modified WKT is
        // written back to the content field (as EWKT, so that the ORM will know
        // to transform back to original SRID).
        _module.layers.vector.events.on({"featuremodified" : _module.modify_wkt});
        _module.layers.vector.events.on({"featureadded" : _module.add_wkt});
        if (wkt){
            if (_module.modifiable){
                _module.enableEditing();
            }
        } else {
            _module.enableDrawing();
        }
    };
    root[moduleName] = _module;
}(this);
