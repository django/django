module("admin.core.date");
test('Date.getTwelveHours', function() {
    // 0:00 -> 12
    equal(
        new Date(2011, 0, 1, 0, 0).getTwelveHours(),
        12,
        '0:00'
    );

    // 11:00 -> 11
    equal(
        new Date(2011, 0, 1, 11, 0).getTwelveHours(),
        11,
        '11:00'
    );

    // 16:00 -> 4
    equal(
        new Date(2011, 0, 1, 16, 0).getTwelveHours(),
        4,
        '16:00'
    );
});

test('Date.getTwoDigitMonth', function() {
    // jan 1
    equal(
        new Date(2011, 0, 1).getTwoDigitMonth(),
        '01',
        'jan 1'
    );

    // oct 1
    equal(
        new Date(2011, 9, 1).getTwoDigitMonth(),
        '10',
        'oct 1'
    );
});

test('Date.getTwoDigitDate', function() {
    // jan 1
    equal(
        new Date(2011, 0, 1).getTwoDigitDate(),
        '01',
        'jan 1'
    );

    // jan 15
    equal(
        new Date(2011, 0, 15).getTwoDigitDate(),
        '15',
        'jan 15'
    );
});

test('Date.getTwoDigitTwelveHour', function() {
    // 0:00 -> '12'
    equal(
        new Date(2011, 0, 1, 0, 0).getTwoDigitTwelveHour(),
        '12',
        '0:00'
    );

    // 4:00
    equal(
        new Date(2011, 0, 1, 4, 0).getTwoDigitTwelveHour(),
        '04',
        '4:00'
    );

    // 22:00
    equal(new Date(2011, 0, 1, 22, 0).getTwoDigitTwelveHour(),
      '10', '22:00');
});

test('Date.getTwoDigitHour', function() {
  expect(0);
});

test('Date.getTwoDigitMinute', function() {
  expect(0);
});

test('Date.getTwoDigitSecond', function() {
  expect(0);
});

test('Date.getHourMinute', function() {
  expect(0);
});

test('Date.getHourMinuteSecond', function() {
  expect(0);
});

test('Date.strftime', function() {
  expect(0);
});
