/* global QUnit, RelatedObjectLookups */
'use strict';

QUnit.module('admin.RelatedObjectLookups', {
    beforeEach: function() {
        const $ = django.jQuery;
        $('#qunit-fixture').append(`
            <input type="text" id="test_id" name="test" />
            <input type="text" id="many_test_id" name="many_test" class="vManyToManyRawIdAdminField" />
        `);
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

QUnit.test('dismissRelatedLookupPopup triggers change event for single value field', function(assert) {
    assert.timeout(1000);
    const done = assert.async();
    const $ = django.jQuery;
    const testId = 'test_id';
    const newValue = '123';
    const mockWin = {
        name: testId,
        close: function() {}
    };
    let changeTriggered = false;
    $('#test_id').on('change', function() {
        changeTriggered = true;
        assert.equal(this.value, newValue, 'Value should be updated');
        done();
    });
    window.dismissRelatedLookupPopup(mockWin, newValue);
    assert.true(changeTriggered, 'Change event should be triggered');
});

QUnit.test('dismissRelatedLookupPopup triggers change event for many-to-many field', function(assert) {
    assert.timeout(1000);
    const $ = django.jQuery;
    const testId = 'many_test_id';
    const existingValue = '1,2';
    const newValue = '3';
    $('#many_test_id').val(existingValue);
    const mockWin = {
        name: testId,
        close: function() {}
    };
    let changeTriggered = false;
    $('#many_test_id').on('change', function() {
        changeTriggered = true;
        assert.equal(this.value, existingValue + ',' + newValue, 'Value should be appended for many-to-many fields');
    });
    window.dismissRelatedLookupPopup(mockWin, newValue);
    assert.true(changeTriggered, 'Change event should be triggered');
});
