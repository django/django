/* global QUnit, SelectBox */
'use strict';

QUnit.module('admin.SelectBox');

QUnit.test('init: no options', function(assert) {
    const $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    SelectBox.init('id');
    assert.equal(SelectBox.cache.id.length, 0);
});

QUnit.test('filter', function(assert) {
    const $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    $('<option value="0">A</option>').appendTo('#id');
    $('<option value="1">B</option>').appendTo('#id');
    SelectBox.init('id');
    assert.equal($('#id option').length, 2);
    SelectBox.filter('id', "A");
    assert.equal($('#id option').length, 1);
    assert.equal($('#id option').text(), "A");
});

QUnit.test('option with group', function(assert) {
    const $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    const a = $('<optgroup label="GroupA">').appendTo('#id');
    const b = $('<optgroup label="GroupB">').appendTo('#id');
    $('<option value="0">A</option>').appendTo(a);
    $('<option value="1">B</option>').appendTo(b);
    $('<option value="2">C</option>').appendTo(b);
    SelectBox.init('id');
    assert.equal($('#id optgroup').length, 2);
    assert.equal(a.children().length, 1);
    assert.equal(b.children().length, 2);
});

