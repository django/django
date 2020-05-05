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

QUnit.test('preserve scroll position', function(assert) {
    const $ = django.jQuery;
    const optionsCount = 100;
    $('<select id="from_id" multiple></select>').appendTo('#qunit-fixture');
    $('<select id="to_id" multiple></select>').appendTo('#qunit-fixture');
    const fromSelectBox = document.getElementById('from_id');
    const toSelectBox = document.getElementById('to_id');
    for (let i = 0; i < optionsCount; i++) {
        fromSelectBox.appendChild(new Option());
    }
    SelectBox.init('from_id');
    SelectBox.init('to_id');
    const selectedOptions = [97, 98, 99];
    for (const index of selectedOptions) {
        fromSelectBox.options[index].selected = true;
        fromSelectBox.options[index].scrollIntoView();
    }
    assert.equal(fromSelectBox.options.length, optionsCount);
    SelectBox.move('from_id', 'to_id');
    assert.equal(fromSelectBox.options.length, optionsCount - selectedOptions.length);
    assert.equal(toSelectBox.options.length, selectedOptions.length);
    assert.notEqual(fromSelectBox.scrollTop, 0);
});
