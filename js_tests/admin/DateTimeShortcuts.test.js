/* global module, test, DateTimeShortcuts */
/* eslint global-strict: 0, strict: 0 */
'use strict';

module('admin.DateTimeShortcuts');

test('init', function(assert) {
    var $ = django.jQuery;

    var dateField = $('<input type="text" class="vDateField" value="2015-03-16"><br>');
    $('#qunit-fixture').append(dateField);

    DateTimeShortcuts.init();

    var shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Today');
    assert.equal(shortcuts.find('a:last .date-icon').length, 1);

    // timezoneOffset should be 0 when no timezone offset is set in the body attribute, otherwise incorrect timezone
    // warnings may appear on date and time widgets (#25845).
    assert.equal(DateTimeShortcuts.timezoneOffset, 0);
});
