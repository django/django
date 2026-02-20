/* global QUnit, DateTimeShortcuts */
'use strict';

QUnit.module('admin.DateTimeShortcuts');

QUnit.test('init', function(assert) {
    const $ = django.jQuery;

    const dateField = $('<input type="text" class="vDateField" value="2015-03-16"><br>');
    $('#qunit-fixture').append(dateField);

    DateTimeShortcuts.init();

    const shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Today');
    assert.equal(shortcuts.find('a:last .date-icon').length, 1);

    // To prevent incorrect timezone warnings on date/time widgets, timezoneOffset
    // should be 0 when a timezone offset isn't set in the HTML body attribute.
    assert.equal(DateTimeShortcuts.timezoneOffset, 0);
});

QUnit.test('custom time shortcuts', function(assert) {
    const $ = django.jQuery;
    const timeField = $('<input type="text" name="time_test" class="vTimeField">');
    $('#qunit-fixture').append(timeField);
    DateTimeShortcuts.clockHours.time_test = [['3 a.m.', 3]];
    DateTimeShortcuts.init();
    assert.equal($('.clockbox').find('a').first().text(), '3 a.m.');
});

QUnit.test('time zone offset warning - single field', function(assert) {
    const $ = django.jQuery;
    const savedOffset = $('body').attr('data-admin-utc-offset');
    // Single date or time field.
    const timeField = $('<input id="id_updated_at" type="text" name="updated_at" class="vTimeField">');
    $('#qunit-fixture').append(timeField);
    $('body').attr('data-admin-utc-offset', new Date().getTimezoneOffset() * -60 + 3600);
    DateTimeShortcuts.init();
    $('body').attr('data-admin-utc-offset', savedOffset);
    assert.equal($('.timezonewarning').text(), 'Note: You are 1 hour behind server time.');
    assert.equal($('.timezonewarning').attr("id"), "id_updated_at_timezone_warning_helptext");
});

QUnit.test('time zone offset warning - date and time field', function(assert) {
    const $ = django.jQuery;
    const savedOffset = $('body').attr('data-admin-utc-offset');
    // DateTimeField with fieldset containing date and time inputs.
    const dateTimeField = '<p class="datetime">' +
    '<input id="id_updated_at_0" type="text" name="updated_at_0" class="vDateField">' +
    '<input id="id_updated_at_1" type="text" name="updated_at_1" class="vTimeField">' +
    '</p>';
    $('#qunit-fixture').append($(dateTimeField));
    $('body').attr('data-admin-utc-offset', new Date().getTimezoneOffset() * -60 + 3600);
    DateTimeShortcuts.init();
    $('body').attr('data-admin-utc-offset', savedOffset);
    assert.equal($('.timezonewarning').attr("id"), "id_updated_at_timezone_warning_helptext");
    assert.ok($('.timezonewarning').next().is('p.datetime'));
});

QUnit.test('time zone warning text position with error list', function(assert) {
    const $ = django.jQuery;
    const savedOffset = $('body').attr('data-admin-utc-offset');
    const dateTimeField = '<ul class="errorlist"><li>This field is required.</li></ul>' +
    '<p class="datetime">' +
    '<input id="id_updated_at_0" type="text" name="updated_at_0" class="vDateField">' +
    '<input id="id_updated_at_1" type="text" name="updated_at_1" class="vTimeField">' +
    '</p>';
    $('#qunit-fixture').append($(dateTimeField));
    $('body').attr('data-admin-utc-offset', new Date().getTimezoneOffset() * -60 + 3600);
    DateTimeShortcuts.init();
    $('body').attr('data-admin-utc-offset', savedOffset);
    assert.ok($('.timezonewarning').next().is('ul.errorlist'));
});

QUnit.test('time zone warning text not duplicate', function(assert) {
    const $ = django.jQuery;
    const savedOffset = $('body').attr('data-admin-utc-offset');
    const dateTimeField = '<div class="help timezonewarning">' +
    "Note: You are 9hours ahead of server time.</div>" +
    '<p class="datetime">' +
    '<input id="id_updated_at_0" type="text" name="updated_at_0" class="vDateField">' +
    '<input id="id_updated_at_1" type="text" name="updated_at_1" class="vTimeField">' +
    '</p>';
    $('#qunit-fixture').append($(dateTimeField));
    $('body').attr('data-admin-utc-offset', new Date().getTimezoneOffset() * -60 + 3600);
    DateTimeShortcuts.init();
    $('body').attr('data-admin-utc-offset', savedOffset);
    assert.equal($('#qunit-fixture .timezonewarning').length, 1);
});
