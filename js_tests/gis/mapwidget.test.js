/* global QUnit, MapWidget */
'use strict';

QUnit.module('gis.OLMapWidget');

QUnit.test('MapWidget.featureAdded', function(assert) {
    const options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    const widget = new MapWidget(options);
    assert.equal(widget.featureCollection.getLength(), 1);
    widget.serializeFeatures();
    assert.equal(
        document.getElementById('id_point').value,
        '{"type":"Point","coordinates":[7.8177,47.397]}',
        'Point added to vector layer'
    );
});

QUnit.test('MapWidget.map_srid', function(assert) {
    const options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    const widget = new MapWidget(options);
    assert.equal(widget.map.getView().getProjection().getCode(), 'EPSG:3857', 'SRID 3857');
});

QUnit.test('MapWidget.defaultCenter', function(assert) {
    const options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    let widget = new MapWidget(options);
    assert.equal(widget.defaultCenter().toString(), '0,0', 'Default center at 0, 0');
    options.default_lat = 47.08;
    options.default_lon = 6.81;
    widget = new MapWidget(options);
    assert.equal(
        widget.defaultCenter().toString(),
        '6.81,47.08',
        'Default center at 6.81, 47.08'
    );
    assert.equal(widget.map.getView().getZoom(), 17);
});

QUnit.test('MapWidget.interactions', function(assert) {
    const options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    const widget = new MapWidget(options);
    assert.equal(Object.keys(widget.interactions).length, 2);
    assert.equal(widget.interactions.draw.getActive(), false, "Draw is inactive with an existing point");
    assert.equal(widget.interactions.modify.getActive(), true, "Modify is active with an existing point");
});

QUnit.test('MapWidget.clearFeatures', function(assert) {
    const options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    const widget = new MapWidget(options);
    const initial_value = document.getElementById('id_point').value;
    widget.clearFeatures();
    assert.equal(document.getElementById('id_point').value, "");
    document.getElementById('id_point').value = initial_value;
});

QUnit.test('MapWidget.multipolygon', function(assert) {
    const options = {id: 'id_multipolygon', map_id: 'id_multipolygon_map', geom_name: 'MultiPolygon'};
    const widget = new MapWidget(options);
    assert.ok(widget.options.is_collection);
    assert.equal(widget.interactions.draw.getActive(), true, "Draw is active with no existing content");
});

QUnit.test('MapWidget.IsCollection', function(assert) {
    const options = {id: 'id_point', map_id: 'id_point_map', geom_name: 'Point'};
    let widget = new MapWidget(options);
    assert.notOk(widget.options.is_collection);
    // Empty the default initial Point
    document.getElementById('id_point').value = "";

    options.geom_name = 'Polygon';
    widget = new MapWidget(options);
    assert.notOk(widget.options.is_collection);

    options.geom_name = 'LineString';
    widget = new MapWidget(options);
    assert.notOk(widget.options.is_collection);

    options.geom_name = 'MultiPoint';
    widget = new MapWidget(options);
    assert.ok(widget.options.is_collection);

    options.geom_name = 'MultiPolygon';
    widget = new MapWidget(options);
    assert.ok(widget.options.is_collection);

    options.geom_name = 'MultiLineString';
    widget = new MapWidget(options);
    assert.ok(widget.options.is_collection);

    options.geom_name = 'GeometryCollection';
    widget = new MapWidget(options);
    assert.ok(widget.options.is_collection);
});
