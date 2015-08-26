/* global module, test, SelectBox */
/* eslint global-strict: 0, strict: 0 */
'use strict';

module('admin.SelectBox');

test('init: no options', function(assert) {
    var $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    SelectBox.init('id');
    assert.equal(SelectBox.cache.id.length, 0);
});

test('filter', function(assert) {
    var $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    $('<option value="0">A</option>').appendTo('#id');
    $('<option value="1">B</option>').appendTo('#id');
    SelectBox.init('id');
    assert.equal($('#id option').length, 2);
    SelectBox.filter('id', "A");
    assert.equal($('#id option').length, 1);
    assert.equal($('#id option').text(), "A");
});
