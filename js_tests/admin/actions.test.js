/* global QUnit */
/* eslint strict: 0 */
'use strict';

QUnit.module('admin.actions', {
    beforeEach: function() {
        // Number of results shown on page
        /* eslint-disable */
        window._actions_icnt = '100';
        /* eslint-enable */

        const $ = django.jQuery;
        $('#qunit-fixture').append($('#result-table').text());

        $('tr input.action-select').actions();
    }
});

QUnit.test('check', function(assert) {
    const $ = django.jQuery;
    assert.notOk($('.action-select').is(':checked'));
    $('#action-toggle').click();
    assert.ok($('.action-select').is(':checked'));
});
