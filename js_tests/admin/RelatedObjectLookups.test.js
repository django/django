/* global QUnit, RelatedObjectLookups */
'use strict';

QUnit.module('admin.RelatedObjectLookups', {
    beforeEach: function() {
        const $ = django.jQuery;
        $('#qunit-fixture').append(`
            <input type="text" id="test_id" name="test" />
            <input type="text" id="many_test_id" name="many_test" class="vManyToManyRawIdAdminField" />
        `);
        window.relatedWindows = window.relatedWindows || [];
    }
});

QUnit.test('dismissRelatedLookupPopup closes popup window', function(assert) {
    const testId = 'test_id';
    let windowClosed = false;
    const mockWin = {
        name: testId,
        close: function() {
            windowClosed = true;
        }
    };
    window.dismissRelatedLookupPopup(mockWin, '123');
    assert.true(windowClosed, 'Popup window should be closed');
});

QUnit.test('dismissRelatedLookupPopup removes window from relatedWindows array', function(assert) {
    const testId = 'test_id';
    const mockWin = {
        name: testId,
        close: function() {}
    };
    window.relatedWindows.push(mockWin);
    assert.equal(window.relatedWindows.indexOf(mockWin), 0, 'Window should be in relatedWindows array');
    window.dismissRelatedLookupPopup(mockWin, '123');
    assert.equal(window.relatedWindows.indexOf(mockWin), -1, 'Window should be removed from relatedWindows array');
});
