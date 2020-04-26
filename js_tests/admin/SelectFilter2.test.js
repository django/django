/* global QUnit, SelectFilter */
'use strict';

QUnit.module('admin.SelectFilter2');

QUnit.test('init', function(assert) {
    const $ = django.jQuery;
    $('<form><select id="id"></select></form>').appendTo('#qunit-fixture');
    $('<option value="0">A</option>').appendTo('#id');
    SelectFilter.init('id', 'things', 0);
    assert.equal($('.selector-available h2').text().trim(), "Available things");
    assert.equal($('.selector-chosen h2').text().trim(), "Chosen things");
    assert.equal(
        $('.selector-available select').outerHeight() + $('.selector-filter').outerHeight(),
        $('.selector-chosen select').height()
    );
    assert.equal($('.selector-chosen select')[0].getAttribute('multiple'), '');
    assert.equal($('.selector-chooseall').text(), "Choose all");
    assert.equal($('.selector-add').text(), "Choose");
    assert.equal($('.selector-remove').text(), "Remove");
    assert.equal($('.selector-clearall').text(), "Remove all");
});
