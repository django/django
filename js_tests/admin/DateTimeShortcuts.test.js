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

QUnit.test("update aria labels - previous and next months", function (assert) {
    const $ = django.jQuery;
    const dateField = $('<input type="text" class="vDateField">');
    $("#qunit-fixture").append(dateField);
    DateTimeShortcuts.init();
    const num = DateTimeShortcuts.calendars.length - 1;
    const cal = DateTimeShortcuts.calendars[num];
    // Set to January 2026
    cal.currentMonth = 1;
    cal.currentYear = 2026;
    DateTimeShortcuts.updateNavAriaLabels(num);
    const cal_box = document.getElementById(
        DateTimeShortcuts.calendarDivName1 + num,
    );
    const prevLabel = cal_box
        .querySelector(".calendarnav-previous")
        .getAttribute("aria-label");
    const nextLabel = cal_box
        .querySelector(".calendarnav-next")
        .getAttribute("aria-label");
    assert.equal(prevLabel, "Previous (December 2025)");
    assert.equal(nextLabel, "Next (February 2026)");
});

QUnit.test("today link has aria-label with current date", function (assert) {
    const $ = django.jQuery;
    const dateField = $(
        '<input type="text" class="vDateField" value="2026-04-12"><br>',
    );
    $("#qunit-fixture").append(dateField);
    DateTimeShortcuts.init();
    const todayLink = $(".datetimeshortcuts a:first");
    assert.equal(todayLink.text(), "Today");
    // "Today (April 12, 2026)"
    const today = new Date();
    const formattedDate = today.toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
    });
    const expectedAriaLabel = `Today (${formattedDate})`;
    assert.equal(todayLink.attr("aria-label"), expectedAriaLabel);
});
