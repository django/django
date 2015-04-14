module('admin.core');

test('Date.getTwelveHours', function(assert) {
    assert.equal(new Date(2011, 0, 1, 0, 0).getTwelveHours(), 12, '0:00');
    assert.equal(new Date(2011, 0, 1, 11, 0).getTwelveHours(), 11, '11:00');
    assert.equal(new Date(2011, 0, 1, 16, 0).getTwelveHours(), 4, '16:00');
});

test('Date.getTwoDigitMonth', function(assert) {
    assert.equal(new Date(2011, 0, 1).getTwoDigitMonth(), '01', 'jan 1');
    assert.equal(new Date(2011, 9, 1).getTwoDigitMonth(), '10', 'oct 1');
});

test('Date.getTwoDigitDate', function(assert) {
    assert.equal(new Date(2011, 0, 1).getTwoDigitDate(), '01', 'jan 1');
    assert.equal(new Date(2011, 0, 15).getTwoDigitDate(), '15', 'jan 15');
});

test('Date.getTwoDigitTwelveHour', function(assert) {
    assert.equal(new Date(2011, 0, 1, 0, 0).getTwoDigitTwelveHour(), '12', '0:00');
    assert.equal(new Date(2011, 0, 1, 4, 0).getTwoDigitTwelveHour(), '04', '4:00');
    assert.equal(new Date(2011, 0, 1, 22, 0).getTwoDigitTwelveHour(), '10', '22:00');
});

test('Date.getTwoDigitHour', function(assert) {
    assert.equal(new Date(2014, 6, 1, 9, 0).getTwoDigitHour(), '09', '9:00 am is 09');
    assert.equal(new Date(2014, 6, 1, 11, 0).getTwoDigitHour(), '11', '11:00 am is 11');
});

test('Date.getTwoDigitMinute', function(assert) {
    assert.equal(new Date(2014, 6, 1, 0, 5).getTwoDigitMinute(), '05', '12:05 am is 05');
    assert.equal(new Date(2014, 6, 1, 0, 15).getTwoDigitMinute(), '15', '12:15 am is 15');
});

test('Date.getTwoDigitSecond', function(assert) {
    assert.equal(new Date(2014, 6, 1, 0, 0, 2).getTwoDigitSecond(), '02', '12:00:02 am is 02');
    assert.equal(new Date(2014, 6, 1, 0, 0, 20).getTwoDigitSecond(), '20', '12:00:20 am is 20');
});

test('Date.getHourMinute', function(assert) {
    assert.equal(new Date(2014, 6, 1, 11, 0).getHourMinute(), '11:00', '11:00 am is 11:00');
    assert.equal(new Date(2014, 6, 1, 13, 25).getHourMinute(), '13:25', '1:25 pm is 13:25');
});

test('Date.getHourMinuteSecond', function(assert) {
    assert.equal(new Date(2014, 6, 1, 11, 0, 0).getHourMinuteSecond(), '11:00:00', '11:00 am is 11:00:00');
    assert.equal(new Date(2014, 6, 1, 17, 45, 30).getHourMinuteSecond(), '17:45:30', '5:45:30 pm is 17:45:30');
});

test('Date.strftime', function(assert) {
    var date = new Date(2014, 6, 1, 11, 0, 5);
    assert.equal(date.strftime('%Y-%m-%d %H:%M:%S'), '2014-07-01 11:00:05');
});

test('String.strptime', function(assert) {
    var date = new Date(1988, 1, 26);
    assert.equal('1988-02-26'.strptime('%Y-%m-%d').toString(), date.toString());
    assert.equal('26/02/88'.strptime('%d/%m/%y').toString(), date.toString());
});
