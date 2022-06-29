/* global QUnit, DateTimeShortcuts */
'use strict';

QUnit.module('admin.DateTimeShortcuts');

QUnit.test('init', function(assert) {
    const $ = django.jQuery;

    const dateField = $('<input type="date" class="vDateField" value="2015-03-16"><br>');
    $('#qunit-fixture').append(dateField);

    DateTimeShortcuts.init();

    const shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Today');

    // To prevent incorrect timezone warnings on date/time widgets, timezoneOffset
    // should be 0 when a timezone offset isn't set in the HTML body attribute.
    assert.equal(DateTimeShortcuts.timezoneOffset, 0);
});

QUnit.test('custom time shortcuts', function(assert) {
    const $ = django.jQuery;
    const timeField = $('<input type="time" class="vTimeField">');
    $('#qunit-fixture').append(timeField);

    DateTimeShortcuts.init();

    const shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Now');
});

QUnit.test('time zone offset warning', function(assert) {
    const $ = django.jQuery;
    const savedOffset = $('body').attr('data-admin-utc-offset');
    const timeField = $('<input type="time" class="vTimeField">');
    $('#qunit-fixture').append(timeField);
    $('body').attr('data-admin-utc-offset', new Date().getTimezoneOffset() * -60 + 3600);
    DateTimeShortcuts.init();
    $('body').attr('data-admin-utc-offset', savedOffset);
    assert.equal($('.timezonewarning').text(), 'Note: You are 1 hour behind server time.');
});

QUnit.test('custom datetime-local shortcuts', function(assert) {
    const $ = django.jQuery;
    const dateTimeField = $('<input type="datetime-local" class="vDateTimeField">');
    $('#qunit-fixture').append(dateTimeField);

    DateTimeShortcuts.init();

    const shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Now');
});
