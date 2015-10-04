/* global module, test, MapWidget */
/* eslint global-strict: 0, strict: 0 */
'use strict';

module('gis.OLMapWidget');

test('MapWidget.featureAdded', function(assert) {
    var options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    var widget = new MapWidget(options);
    assert.equal(widget.layers.vector.features.length, 1);
    assert.equal(
        widget.layers.vector.features[0].geometry.toString(),
        'POINT(7.8177 47.397)',
        'Point addded to vector layer'
    );
});

test('MapWidget.map_srid', function(assert) {
    var options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    var widget = new MapWidget(options);
    assert.equal(widget.options.map_srid, 4326, 'SRID 4326');
});

test('MapWidget.defaultCenter', function(assert) {
    var options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    var widget = new MapWidget(options);
    assert.equal(widget.defaultCenter().toString(), 'lon=0,lat=0', 'Default center at 0, 0');
    options.default_lat = 47.08;
    options.default_lon = 6.81;
    widget = new MapWidget(options);
    assert.equal(
        widget.defaultCenter().toString(),
        'lon=6.81,lat=47.08',
        'Default center at 6.81, 47.08'
    );
});

test('MapWidget.getControls', function(assert) {
    var options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    var widget = new MapWidget(options);
    widget.getControls(widget.layers.vector);
    assert.equal(widget.controls.length, 3);
    assert.equal(widget.controls[0].displayClass, 'olControlNavigation', 'Navigation control');
    assert.equal(widget.controls[1].displayClass, 'olControlDrawFeaturePoint', 'Draw control');
    assert.equal(widget.controls[2].displayClass, 'olControlModifyFeature', 'Modify control');
});
