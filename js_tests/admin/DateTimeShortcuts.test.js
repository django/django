/* global QUnit, DateTimeShortcuts */
/* eslint global-strict: 0, strict: 0 */
'use strict';

QUnit.module('admin.DateTimeShortcuts');

QUnit.test('init', function(assert) {
    var $ = django.jQuery;

    var dateField = $('<input type="text" class="vDateField" value="2015-03-16"><br>');
    $('#qunit-fixture').append(dateField);

    DateTimeShortcuts.init();

    var shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Today');
    assert.equal(shortcuts.find('a:last .date-icon').length, 1);

    // To prevent incorrect timezone warnings on date/time widgets, timezoneOffset
    // should be 0 when a timezone offset isn't set in the HTML body attribute.
    assert.equal(DateTimeShortcuts.timezoneOffset, 0);
});

QUnit.test('custom time shortcuts', function(assert) {
    var $ = django.jQuery;
    var timeField = $('<input type="text" name="time_test" class="vTimeField">');
    $('#qunit-fixture').append(timeField);
    DateTimeShortcuts.clockHours.time_test = [['3 a.m.', 3]];
    DateTimeShortcuts.init();
    assert.equal($('.clockbox').find('a').first().text(), '3 a.m.');
});
