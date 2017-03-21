/* global QUnit */
/* eslint global-strict: 0, strict: 0 */
'use strict';

QUnit.module('admin.core');

QUnit.test('Date.getTwelveHours', function(assert) {
    assert.equal(new Date(2011, 0, 1, 0, 0).getTwelveHours(), 12, '0:00');
    assert.equal(new Date(2011, 0, 1, 11, 0).getTwelveHours(), 11, '11:00');
    assert.equal(new Date(2011, 0, 1, 16, 0).getTwelveHours(), 4, '16:00');
});

QUnit.test('Date.getTwoDigitMonth', function(assert) {
    assert.equal(new Date(2011, 0, 1).getTwoDigitMonth(), '01', 'jan 1');
    assert.equal(new Date(2011, 9, 1).getTwoDigitMonth(), '10', 'oct 1');
});

QUnit.test('Date.getTwoDigitDate', function(assert) {
    assert.equal(new Date(2011, 0, 1).getTwoDigitDate(), '01', 'jan 1');
    assert.equal(new Date(2011, 0, 15).getTwoDigitDate(), '15', 'jan 15');
});

QUnit.test('Date.getTwoDigitTwelveHour', function(assert) {
    assert.equal(new Date(2011, 0, 1, 0, 0).getTwoDigitTwelveHour(), '12', '0:00');
    assert.equal(new Date(2011, 0, 1, 4, 0).getTwoDigitTwelveHour(), '04', '4:00');
    assert.equal(new Date(2011, 0, 1, 22, 0).getTwoDigitTwelveHour(), '10', '22:00');
});

QUnit.test('Date.getTwoDigitHour', function(assert) {
    assert.equal(new Date(2014, 6, 1, 9, 0).getTwoDigitHour(), '09', '9:00 am is 09');
    assert.equal(new Date(2014, 6, 1, 11, 0).getTwoDigitHour(), '11', '11:00 am is 11');
});

QUnit.test('Date.getTwoDigitMinute', function(assert) {
    assert.equal(new Date(2014, 6, 1, 0, 5).getTwoDigitMinute(), '05', '12:05 am is 05');
    assert.equal(new Date(2014, 6, 1, 0, 15).getTwoDigitMinute(), '15', '12:15 am is 15');
});

QUnit.test('Date.getTwoDigitSecond', function(assert) {
    assert.equal(new Date(2014, 6, 1, 0, 0, 2).getTwoDigitSecond(), '02', '12:00:02 am is 02');
    assert.equal(new Date(2014, 6, 1, 0, 0, 20).getTwoDigitSecond(), '20', '12:00:20 am is 20');
});

QUnit.test('Date.getHourMinute', function(assert) {
    assert.equal(new Date(2014, 6, 1, 11, 0).getHourMinute(), '11:00', '11:00 am is 11:00');
    assert.equal(new Date(2014, 6, 1, 13, 25).getHourMinute(), '13:25', '1:25 pm is 13:25');
});

QUnit.test('Date.getHourMinuteSecond', function(assert) {
    assert.equal(new Date(2014, 6, 1, 11, 0, 0).getHourMinuteSecond(), '11:00:00', '11:00 am is 11:00:00');
    assert.equal(new Date(2014, 6, 1, 17, 45, 30).getHourMinuteSecond(), '17:45:30', '5:45:30 pm is 17:45:30');
});

QUnit.test('Date.strftime', function(assert) {
    var date = new Date(2014, 6, 1, 11, 0, 5);
    assert.equal(date.strftime('%Y-%m-%d %H:%M:%S'), '2014-07-01 11:00:05');
    assert.equal(date.strftime('%B %d, %Y'), 'July 01, 2014');
});

QUnit.test('String.strptime', function(assert) {
    // Use UTC functions for extracting dates since the calendar uses them as
    // well. Month numbering starts with 0 (January).
    var firstParsedDate = '1988-02-26'.strptime('%Y-%m-%d');
    assert.equal(firstParsedDate.getUTCDate(), 26);
    assert.equal(firstParsedDate.getUTCMonth(), 1);
    assert.equal(firstParsedDate.getUTCFullYear(), 1988);

    var secondParsedDate = '26/02/88'.strptime('%d/%m/%y');
    assert.equal(secondParsedDate.getUTCDate(), 26);
    assert.equal(secondParsedDate.getUTCMonth(), 1);
    assert.equal(secondParsedDate.getUTCFullYear(), 1988);

    var format = django.get_format('DATE_INPUT_FORMATS')[0];
    var thirdParsedDate = '1983-11-20'.strptime(format);

    assert.equal(thirdParsedDate.getUTCDate(), 20);
    assert.equal(thirdParsedDate.getUTCMonth(), 10);
    assert.equal(thirdParsedDate.getUTCFullYear(), 1983);

    // Extracting from a Date object with local time must give the correct
    // result. Without proper conversion, timezones from GMT+0100 to GMT+1200
    // gives a date one day earlier than necessary, e.g. converting local time
    // Feb 26, 1988 00:00:00 EEST is Feb 25, 21:00:00 UTC.

    // Checking timezones from GMT+0100 to GMT+1200
    var i, tz, date;
    for (i = 1; i <= 12; i++) {
        tz = i > 9 ? '' + i : '0' + i;
        date = new Date(Date.parse('Feb 26, 1988 00:00:00 GMT+' + tz + '00'));
        assert.notEqual(date.getUTCDate(), 26);
        assert.equal(date.getUTCDate(), 25);
        assert.equal(date.getUTCMonth(), 1);
        assert.equal(date.getUTCFullYear(), 1988);
    }

    // Checking timezones from GMT+0000 to GMT-1100
    for (i = 0; i <= 11; i++) {
        tz = i > 9 ? '' + i : '0' + i;
        date = new Date(Date.parse('Feb 26, 1988 00:00:00 GMT-' + tz + '00'));
        assert.equal(date.getUTCDate(), 26);
        assert.equal(date.getUTCMonth(), 1);
        assert.equal(date.getUTCFullYear(), 1988);
    }
});
