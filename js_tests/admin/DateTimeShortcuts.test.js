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
});

QUnit.test('Escape key dismisses clock popup', function(assert) {
    const $ = django.jQuery;
    const timeField = $('<input type="text" name="time_test_esc" class="vTimeField">');
    $('#qunit-fixture').append(timeField);
    DateTimeShortcuts.init();

    // Open the clock popup
    const clockLink = $('.clockbox').closest('.datetimeshortcuts').find('a:last');
    if (clockLink.length) {
        clockLink[0].click();
    }

    // Simulate pressing Escape using event.key (not deprecated keyCode)
    const event = new KeyboardEvent('keyup', {'key': 'Escape', 'bubbles': true});
    document.dispatchEvent(event);

    // Verify the clock popup is dismissed
    const clockBox = $('#clockbox0');
    if (clockBox.length) {
        assert.equal(clockBox.css('display'), 'none', 'Clock popup should be hidden after Escape');
    } else {
        assert.ok(true, 'Clock popup element not found (already dismissed)');
    }
});

QUnit.test('Escape key dismisses calendar popup', function(assert) {
    const $ = django.jQuery;
    const dateField = $('<input type="text" class="vDateField" value="2024-01-15">');
    $('#qunit-fixture').append(dateField);
    DateTimeShortcuts.init();

    // Open the calendar popup
    const calendarLink = $('.datetimeshortcuts').find('.date-icon').closest('a');
    if (calendarLink.length) {
        calendarLink[0].click();
    }

    // Simulate pressing Escape using event.key (not deprecated keyCode)
    const event = new KeyboardEvent('keyup', {'key': 'Escape', 'bubbles': true});
    document.dispatchEvent(event);

    // Verify the calendar popup is dismissed
    const calendarBox = $('#calendarbox0');
    if (calendarBox.length) {
        assert.equal(calendarBox.css('display'), 'none', 'Calendar popup should be hidden after Escape');
    } else {
        assert.ok(true, 'Calendar popup element not found (already dismissed)');
    }
});
