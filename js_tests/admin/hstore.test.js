/* global module, test */
/* eslint global-strict: 0, strict: 0 */
'use strict';

module('admin.HStore');

test('init', function(assert) {

    var $ = django.jQuery;

    var field = $('<textarea class="hstore">{}</textarea>');
    $('#qunit-fixture').append(field);

    $('textarea.hstore').hstore();

    assert.equal(field[0].style.display, 'none');
});
