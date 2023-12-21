/* global QUnit, DateTimeISOShortcuts */
'use strict';

QUnit.module('admin.DateTimeISOShortcuts');

QUnit.test('init', function(assert) {
    const $ = django.jQuery;

    const dateField = $('<input type="date" class="vDateField" value="2015-03-16"><br>');
    $('#qunit-fixture').append(dateField);

    DateTimeISOShortcuts.init();

    const shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Today');

    // To prevent incorrect timezone warnings on date/time widgets, timezoneOffset
    // should be 0 when a timezone offset isn't set in the HTML body attribute.
    assert.equal(DateTimeISOShortcuts.timezoneOffset, 0);
});

QUnit.test('custom time shortcuts', function(assert) {
    const $ = django.jQuery;
    const timeField = $('<input type="time" class="vTimeField">');
    $('#qunit-fixture').append(timeField);
    DateTimeISOShortcuts.init();
    const shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Now');
});

QUnit.test('time zone offset warning', function(assert) {
    const $ = django.jQuery;
    const savedServerOffsetFn = DateTimeISOShortcuts.serverOffset;
    const timeField = $('<input type="time" class="vTimeField">');
    $('#qunit-fixture').append(timeField);
    DateTimeISOShortcuts.serverOffset = function() {
        return new Date().getTimezoneOffset() * -60 + 3600;
    };
    DateTimeISOShortcuts.init();
    DateTimeISOShortcuts.serverOffset = savedServerOffsetFn;
    assert.equal($('.timezonewarning').text(), 'Note: You are 1 hour behind server time.');
});

QUnit.test('custom datetime-local shortcuts', function(assert) {
    const $ = django.jQuery;
    const dateTimeField = $('<input type="datetime-local" class="vDateTimeField">');
    $('#qunit-fixture').append(dateTimeField);
    DateTimeISOShortcuts.init();
    const shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Now');
});
