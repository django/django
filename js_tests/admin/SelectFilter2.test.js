/* global module, test, SelectFilter */
/* eslint global-strict: 0, strict: 0 */
'use strict';

module('admin.SelectFilter2');

test('init', function(assert) {
    var $ = django.jQuery;
    $('<form><select id="id"></select></form>').appendTo('#qunit-fixture');
    $('<option value="0">A</option>').appendTo('#id');
    SelectFilter.init('id', 'things', 0);
    assert.equal($('.selector-available h2').text().trim(), "Available things");
    assert.equal($('.selector-chosen h2').text().trim(), "Chosen things");
    assert.equal($('.selector-chooseall').text(), "Choose all");
    assert.equal($('.selector-add').text(), "Choose");
    assert.equal($('.selector-remove').text(), "Remove");
    assert.equal($('.selector-clearall').text(), "Remove all");
});
