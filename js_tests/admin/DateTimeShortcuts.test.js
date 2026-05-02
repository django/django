/* global QUnit, DateTimeShortcuts */
"use strict";

QUnit.module("admin.DateTimeShortcuts", {
    afterEach: function () {
        const $ = django.jQuery;
        $("body")
            .removeAttr("data-admin-server-timezone")
            .removeAttr("data-admin-utc-offset");
        $(".timezonewarning").remove();
    },
});

QUnit.test("init", function (assert) {
    const $ = django.jQuery;

    const dateField = $(
        '<input type="text" class="vDateField" value="2015-03-16"><br>',
    );
    $("#qunit-fixture").append(dateField);

    DateTimeShortcuts.init();

    const shortcuts = $(".datetimeshortcuts");
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find("a:first").text(), "Today");
    assert.equal(shortcuts.find("a:last .date-icon").length, 1);

    // To prevent incorrect timezone warnings on date/time widgets, timezoneOffset
    // should be 0 when a timezone offset isn't set in the HTML body attribute.
    assert.equal(DateTimeShortcuts.timezoneOffset, 0);
});

QUnit.test("custom time shortcuts", function (assert) {
    const $ = django.jQuery;
    const timeField = $(
        '<input type="text" name="time_test" class="vTimeField">',
    );
    $("#qunit-fixture").append(timeField);
    DateTimeShortcuts.clockHours.time_test = [["3 a.m.", 3]];
    DateTimeShortcuts.init();
    assert.equal($(".clockbox").find("a").first().text(), "3 a.m.");
});

QUnit.test("time zone offset warning - single field", function (assert) {
    const $ = django.jQuery;
    const savedOffset = $("body").attr("data-admin-utc-offset");
    // Single date or time field.
    const timeField = $(
        '<input id="id_updated_at" type="text" name="updated_at" class="vTimeField">',
    );
    $("#qunit-fixture").append(timeField);
    $("body").attr(
        "data-admin-utc-offset",
        new Date().getTimezoneOffset() * -60 + 3600,
    );
    $("body").attr("data-admin-server-timezone", "America/Chicago");
    DateTimeShortcuts.init();
    $("body").attr("data-admin-utc-offset", savedOffset);
    assert.equal(
        $(".timezonewarning").text(),
        "Note: Enter times in the America/Chicago timezone. " +
            "(You are 1 hour behind.)",
    );
    assert.equal(
        $(".timezonewarning").attr("id"),
        "id_updated_at_timezone_warning_helptext",
    );
});

QUnit.test("time zone offset warning - date and time field", function (assert) {
    const $ = django.jQuery;
    const savedOffset = $("body").attr("data-admin-utc-offset");
    // DateTimeField with fieldset containing date and time inputs.
    const dateTimeField =
        '<p class="datetime">' +
        '<input id="id_updated_at_0" type="text" name="updated_at_0" class="vDateField">' +
        '<input id="id_updated_at_1" type="text" name="updated_at_1" class="vTimeField">' +
        "</p>";
    $("#qunit-fixture").append($(dateTimeField));
    $("body").attr(
        "data-admin-utc-offset",
        new Date().getTimezoneOffset() * -60 + 3600,
    );
    DateTimeShortcuts.init();
    $("body").attr("data-admin-utc-offset", savedOffset);
    assert.equal(
        $(".timezonewarning").text(),
        "Note: Enter times in the server timezone. (You are 1 hour behind.)",
    );
    assert.equal(
        $(".timezonewarning").attr("id"),
        "id_updated_at_timezone_warning_helptext",
    );
});

QUnit.test("calendar today highlight without server offset", function (assert) {
    const $ = django.jQuery;
    const calDiv = $('<div id="test-calendar"></div>');
    $("#qunit-fixture").append(calDiv);

    const today = new Date();
    CalendarNamespace.draw(
        today.getMonth() + 1,
        today.getFullYear(),
        "test-calendar",
        function () {},
    );

    const todayCells = calDiv.find("td.today");
    assert.equal(todayCells.length, 1, "Exactly one cell marked as today");
    assert.equal(
        todayCells.find("a").text(),
        String(today.getDate()),
        "Today cell matches local date",
    );
});

QUnit.test("calendar today highlight with server offset", function (assert) {
    const $ = django.jQuery;
    const calDiv = $('<div id="test-calendar"></div>');
    $("#qunit-fixture").append(calDiv);

    // Simulate a server timezone that is 24 hours ahead of the browser.
    const localOffset = new Date().getTimezoneOffset() * -60;
    const serverOffset = localOffset + 86400;
    $("body").attr("data-admin-utc-offset", serverOffset);

    const expectedDate = new Date();
    expectedDate.setTime(
        expectedDate.getTime() + 1000 * (serverOffset - localOffset),
    );

    CalendarNamespace.draw(
        expectedDate.getMonth() + 1,
        expectedDate.getFullYear(),
        "test-calendar",
        function () {},
    );

    const todayCells = calDiv.find("td.today");
    assert.equal(todayCells.length, 1, "Exactly one cell marked as today");
    assert.equal(
        todayCells.find("a").text(),
        String(expectedDate.getDate()),
        "Today cell matches server-adjusted date",
    );
});

QUnit.test("Calendar constructor uses server offset", function (assert) {
    const $ = django.jQuery;
    const calDiv = $('<div id="test-calendar"></div>');
    $("#qunit-fixture").append(calDiv);

    // Simulate a server timezone that is 24 hours ahead of the browser.
    const localOffset = new Date().getTimezoneOffset() * -60;
    const serverOffset = localOffset + 86400;
    $("body").attr("data-admin-utc-offset", serverOffset);

    const expectedDate = new Date();
    expectedDate.setTime(
        expectedDate.getTime() + 1000 * (serverOffset - localOffset),
    );

    const cal = new Calendar("test-calendar", function () {});
    assert.equal(
        cal.currentMonth,
        expectedDate.getMonth() + 1,
        "Calendar month matches server-adjusted date",
    );
    assert.equal(
        cal.currentYear,
        expectedDate.getFullYear(),
        "Calendar year matches server-adjusted date",
    );
});
