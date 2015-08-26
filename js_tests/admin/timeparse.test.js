/* global module, test, parseTimeString */
/* eslint global-strict: 0, strict: 0 */
'use strict';

module('admin.timeparse');

test('parseTimeString', function(assert) {
    function time(then, expected) {
        assert.equal(parseTimeString(then), expected);
    }
    time('9', '09:00');
    time('09', '09:00');
    time('13:00', '13:00');
    time('13.00', '13:00');
    time('9:00', '09:00');
    time('9.00', '09:00');
    time('3 am', '03:00');
    time('3 a.m.', '03:00');
    time('12 am', '00:00');
    time('11 am', '11:00');
    time('12 pm', '12:00');
    time('3am', '03:00');
    time('3.30 am', '03:30');
    time('3:15 a.m.', '03:15');
    time('3.00am', '03:00');
    time('12.00am', '00:00');
    time('11.00am', '11:00');
    time('12.00pm', '12:00');
    time('noon', '12:00');
    time('midnight', '00:00');
    time('something else', 'something else');
});
